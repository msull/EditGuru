import json
import os
import time
from typing import Optional

import click
import logzero
import openai
import pandas as pd
from rich.console import Console
from rich.markdown import Markdown
from rich.status import Status
from simplesingletable import DynamoDbMemory
from supersullytools.llm.agent import ChatAgent
from supersullytools.llm.completions import CompletionHandler
from supersullytools.llm.trackers import GlobalUsageTracker, SessionUsageTracking, TopicUsageTracking
from supersullytools.utils.common_init import get_standard_completion_handler

from edit_guru.agents.ai_developer.config import ConfigManager
from edit_guru.agents.ai_developer.tools import ListFiles

from .agents.ai_developer import ai_developer_agent

package_version = "0.9.0"

# Create a logger instance
logger = logzero.setup_logger(level=logzero.ERROR)


def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if isinstance(e, click.exceptions.Exit):
                raise
            click.echo(f"An error occurred: {e}", err=True)
            raise click.exceptions.Exit(1)

    return wrapper


@click.command("main")
@click.argument("task", required=False)
@click.option("--plan-model", default=None)
@click.option("--model", default="gpt-4o-mini")
@click.option("--approve", is_flag=True, help="Pre-approve the generated plan and automatically execute.")
@click.option("--approve-tools", is_flag=True, help="Pre-approve all tool usage.")
@click.option("-f", is_flag=True, help="Shortcut for --approve and --approve-tools")
@click.option("--max-cost", type=float, default=0.01, help="Maximum cost limit in dollars (default: $0.01)")
@click.option("--use-cwd", is_flag=True)
@click.option("--skip-planning", is_flag=True)
@click.option(
    "--include-file-listing", is_flag=True, help="Send the full file listing of the repo / cwd to the planning step"
)
@click.option("--display-usage", is_flag=True, help="Show usage then quit")
@handle_exceptions
def main(
    task: str,
    approve: bool,
    approve_tools: bool,
    f: bool,
    plan_model: Optional[str],
    model: str,
    max_cost: float,
    use_cwd: bool,
    include_file_listing: bool,
    display_usage: bool,
    skip_planning: bool,
):
    if f:
        approve = True
        approve_tools = True
    completion_handler = get_completion_handler()

    console = Console()
    if display_usage:
        display_data = {}
        for tracker in completion_handler.completion_tracker.trackers:
            if isinstance(tracker, (GlobalUsageTracker, SessionUsageTracking)):
                continue
            if isinstance(tracker, TopicUsageTracking):
                key = tracker.topic
            else:
                key = tracker.__class__.__name__
            this_data = tracker.model_dump(
                mode="json",
                exclude={
                    "transcripts_by_model",
                    "seconds_transcribed_by_model",
                    "resource_id",
                    "created_at",
                    "updated_at",
                    "topic",
                },
            )
            this_data["cost_per_model"] = tracker.compute_cost_per_model()
            display_data[key] = this_data
        click.echo(json.dumps(display_data))
        return
    elif not task:
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        ctx.exit()

    ConfigManager.get_instance().initialize(use_cwd=use_cwd)

    console.print(f"[cyan]Task: {task}[/cyan]")
    try:
        model = completion_handler.get_model_by_name_or_id(model)
    except ValueError:
        raise RuntimeError(
            "Invalid model, must be one of " + ", ".join([x.llm_id for x in completion_handler.available_models])
        )
    if plan_model and not skip_planning:
        try:
            plan_model = completion_handler.get_model_by_name_or_id(plan_model)
        except ValueError:
            raise RuntimeError(
                "Invalid plan model, must be one of "
                + ", ".join([x.llm_id for x in completion_handler.available_models])
            )
    else:
        plan_model = model
    plan_agent = ai_developer_agent(
        model=plan_model, logger=logger, completion_handler=completion_handler, max_tool_calls=0
    )
    action_agent = ai_developer_agent(
        model=model, logger=logger, completion_handler=completion_handler, max_tool_calls=10
    )

    action_agent.replace_user_preferences(
        [
            (
                "I can only see your final message after the task is complete, "
                "so be sure you provide a complete answer without assuming I can read your previous messages"
            ),
            (
                "Do not make personal judgements about the content or the system you are interacting with; I do "
                "not need to know if you think the repo is a compelling resource, for example. Just stick to the facts."
            ),
            (
                "Approach the task step by step -- you shouldn't call al the functions at once, particularly if you "
                "need to get a result and process it before continuing. "
                "You will be able to take multiple turns, so take it slow! "
                "But do call things in parallel when they are not dependent upon each other."
            ),
            (
                "If you edit a file, be sure you read it again before doing another Edit, as your line numbers will "
                "have changed! "
                "If you can do one larger edit rather than multiple small edits (when things are separated by a "
                "several lines for example), even if you have to repeat some existing code, that's usually better."
            ),
        ]
    )
    if skip_planning:
        action_agent.message_from_user(task)
    else:
        click.echo("Generating a plan to accomplish this task...")
        plan = make_a_plan(plan_agent, task, include_file_listing)

        md = Markdown(plan + "\n\n---")
        console.print(md)

        if approve or click.confirm("Proceed with plan", default=True):
            msg = (
                "Please perform the following task and use this plan as a rough guideline"
                f"\n<task>\n{task}\n</task>\n<plan>\n{plan}\n</plan>"
            )
            action_agent.message_from_user(msg)

    confirm_next_loop = True

    session_tracker: SessionUsageTracking = next(
        x for x in completion_handler.completion_tracker.trackers if isinstance(x, SessionUsageTracking)
    )

    while confirm_next_loop or approve_tools or click.confirm("Approve", default=True):
        if action_agent.get_pending_tool_calls():
            action_agent.approve_pending_tool_usage()

        max_cost = run_agent_with_status(action_agent, session_tracker, max_cost)
        pending_tools = action_agent.get_pending_tool_calls()
        if pending_tools and approve_tools:
            continue

        md = Markdown(action_agent.chat_history[-1].content)
        console.print(md)
        if pending_tools:
            click.echo("TOOL USE PENDING")
            for p in pending_tools:
                click.echo(p.tool.name)
                click.echo(p.reason)
        else:
            stats_df = pd.DataFrame(
                {"count": session_tracker.completions_by_model, "cost": session_tracker.compute_cost_per_model()}
            )
            total_count = int(stats_df["count"].sum())
            total_cost = round(stats_df["cost"].sum(), 4)
            click.echo(f"Final Completion Input Tokens: {session_tracker.completions[-1].response.input_tokens}")
            click.echo(f"Final Completion Cost: {session_tracker.completions[-1].response.completion_cost}")
            click.echo(f"Total Completions Made: {total_count}")
            click.echo(f"Total Completions Cost: {total_cost}")
            user_msg = input("Respond to llm (blank line to quit): \n").strip()
            if not user_msg:
                break
            action_agent.message_from_user(user_msg)
            confirm_next_loop = True


def run_agent_with_status(agent: ChatAgent, session_tracker, max_cost):
    console = Console()
    with Status("[bold green]AI is initializing...[/bold green]", spinner="dots", console=console) as status:
        status_msg = "AI is processing..."

        def status_callback_fn(message):
            nonlocal status_msg
            status_msg += "\n" + message
            status.update(f"[bold cyan]{status_msg}[/bold cyan]")

        status_callback_fn(agent.get_current_status_msg())

        # Run the agent loop, passing the callback function
        while agent.working:
            if not check_cost_limit(session_tracker, max_cost):
                current_cost = sum(session_tracker.compute_cost_per_model().values())
                status_callback_fn("Reached cost limit while executing task, asking user for extension...")

                user_extension_prompt = (
                    f"[bold cyan]{status_msg}[/bold cyan]\n\n[red]Cost limit reached: spent so far "
                    f"${current_cost:.4f} / current limit ${max_cost:.4f}"
                    "\nWould you like to extend the cost limit (enter dollar amount or blank to halt)?[/red]\n\n"
                )
                status.stop()

                if extension_amount := console.input(user_extension_prompt):
                    status.start()
                    extension_amount = float(extension_amount)
                    status_callback_fn(f"Extending cost limit by {extension_amount}")
                    max_cost += float(extension_amount)
                else:
                    status_msg = ""
                    status.start()
                    status_callback_fn("User declined cost extension, halting")
                    break
            agent.run_agent(status_callback_fn=status_callback_fn)
            time.sleep(0.01)

        status.update("[bold green]Task complete![/bold green]")
        return max_cost


def make_a_plan(agent: ChatAgent, task: str, include_file_dump: bool) -> str:
    prompt = (
        "How would you accomplish the following using your given tools; "
        "for now just make a plan and tell me, do not take any action.\n"
        "Please keep your response concise, as it will be shown to me "
        "in a terminal console with limited display size.\n"
    )

    if include_file_dump:
        list_files_tool = agent.get_current_tool_by_name(ListFiles.__name__)
        dumped = ListFiles(recursive=True).model_dump()
        file_listing = list_files_tool.invoke_tool(dumped)
        prompt += (
            "Reference specific paths using the provided listing "
            "(rather than planning to ListFiles later) when possible"
        )
        agent.add_to_context("current_file_listing", file_listing)
    prompt += f"\n<task>\n{task}\n</task>"
    agent.message_from_user(prompt)
    while agent.working:
        agent.run_agent()
    return agent.chat_history[-1].content


def get_dynamodb_memory() -> DynamoDbMemory:
    memory = DynamoDbMemory(
        logger=logger,
        table_name=os.environ["EDITGURU_DYNAMODB_TABLE"],
        track_stats=False,
    )
    return memory


"""
export COMPLETION_TRACKING_DYNAMODB_TABLE=MyPrivateInfra-CoreAppStack-completiontrackingtable23B7FCA5-1V8MT3T373R9H
export COMPLETION_TRACKING_BUCKET_NAME=myprivateinfra-coreappsta-completiontrackingbucket-gu3pqjarvcrc

"""


def get_completion_handler() -> CompletionHandler:
    enable_bedrock = os.getenv("EDITGURU_ENABLE_BEDROCK") in ("1", "true", "yes")
    openai_client = openai.Client(api_key=os.environ["EDITGURU_OPENAI_API_KEY"])
    if os.getenv("COMPLETION_TRACKING_DYNAMODB_TABLE") and os.getenv("COMPLETION_TRACKING_BUCKET_NAME"):
        logger.info("Completion tracking enabled")
        # use standard handler with completion tracking
        return get_standard_completion_handler(
            topics=["EditGuru-cli"],
            include_session_tracker=True,
            store_source_tag="EDITGURU",
            logger=logger,
            openai_client=openai_client,
            enable_bedrock=enable_bedrock,
        )
    else:
        return CompletionHandler(logger=logger, enable_bedrock=enable_bedrock, openai_client=openai_client)


def check_cost_limit(session_tracker: SessionUsageTracking, max_cost: float) -> bool:
    current_cost = sum(session_tracker.compute_cost_per_model().values())
    return current_cost < max_cost
