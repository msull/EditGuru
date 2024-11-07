import time
from typing import Optional

import click
import logzero
import pandas as pd
from rich.console import Console
from rich.markdown import Markdown
from rich.status import Status
from supersullytools.llm.agent import ChatAgent
from supersullytools.llm.completions import CompletionHandler
from supersullytools.llm.trackers import CompletionTracker, SessionUsageTracking

from edit_guru.agents.ai_developer.tools import ListFiles

from .agents.ai_developer import ai_developer_agent

package_version = "0.4.0"

# Create a logger instance
logger = logzero.setup_logger(level=logzero.ERROR)


@click.command("main")
@click.argument("task")
@click.option("--plan-model", default=None)
@click.option("--model", default="gpt-4o-mini")
@click.option("--approve", is_flag=True, help="Pre-approve the generated plan and automatically execute.")
@click.option("--approve-tools", is_flag=True, help="Pre-approve all tool usage.")
@click.option("-f", is_flag=True, help="Shortcut for --approve and --approve-tools")
@click.option("--max-cost", type=float, default=0.01, help="Maximum cost limit in dollars (default: $0.01)")
def main(
    task: str, approve: bool, approve_tools: bool, f: bool, plan_model: Optional[str], model: str, max_cost: float
):
    if f:
        approve = True
        approve_tools = True
    session_tracker = SessionUsageTracking()
    trackers = [session_tracker]
    completion_handler = get_completion_handler(trackers)

    try:
        model = completion_handler.get_model_by_name_or_id(model)
    except ValueError:
        raise RuntimeError(
            "Invalid model, must be one of " + ", ".join([x.llm_id for x in completion_handler.available_models])
        )
    if plan_model:
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
        ]
    )
    click.echo("Generating a plan to accomplish this task...")
    plan = make_a_plan(plan_agent, task)

    console = Console()
    md = Markdown(plan + "\n\n---")
    console.print(md)

    if approve or click.confirm("Proceed with plan", default=True):
        msg = (
            "Please perform the following task and use this plan as a rough guideline"
            f"\n<task>\n{task}\n</task>\n<plan>\n{plan}\n</plan>"
        )
        action_agent.message_from_user(msg)

    confirm_next_loop = True

    while confirm_next_loop or approve_tools or click.confirm("Approve", default=True):
        if action_agent.get_pending_tool_calls():
            action_agent.approve_pending_tool_usage()

        run_agent_with_status(action_agent, session_tracker, max_cost)
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
                status_callback_fn(
                    f"[red]Cost limit reached: spent so far ${current_cost:.4f} / current limit ${max_cost:.4f}"
                    "\nWould you like to extend the cost limit (enter dollar amount or blank to halt)?[/red]\n\n"
                )

                if extension_amount := console.input():
                    extension_amount = float(extension_amount)
                    status_callback_fn(f"Extending cost limit by {extension_amount}")
                    max_cost += float(extension_amount)
                else:
                    status_callback_fn("User declined cost extension, halting")
                    break
            agent.run_agent(status_callback_fn=status_callback_fn)
            time.sleep(0.01)

        status.update("[bold green]Task complete![/bold green]")


def make_a_plan(agent: ChatAgent, task: str) -> str:
    prompt = (
        "How would you accomplish the following using your given tools; "
        "for now just make a plan and tell me, do not take any action.\n"
        "Please keep your response concise, as it will be shown to me "
        "in a terminal console with limited display size.\n"
        f"<task>\n{task}\n</task>"
    )
    list_files_tool = agent.get_current_tool_by_name(ListFiles.__name__)
    file_listing = list_files_tool.invoke_tool(ListFiles(recursive=True).model_dump())
    agent.add_to_context("updated_repository_file_listing", file_listing)
    agent.message_from_user(prompt)
    while agent.working:
        agent.run_agent()
    return agent.chat_history[-1].content


def get_completion_handler(trackers) -> CompletionHandler:
    # memory = get_dynamodb_memory()
    completion_tracker = CompletionTracker(memory=None, trackers=trackers)
    return CompletionHandler(
        logger=logger,
        debug_output_prompt_and_response=False,
        completion_tracker=completion_tracker,
        default_max_response_tokens=4096,
        enable_bedrock=True,
    )


if __name__ == "__main__":
    main()


def check_cost_limit(session_tracker: SessionUsageTracking, max_cost: float) -> bool:
    current_cost = sum(session_tracker.compute_cost_per_model().values())
    return current_cost < max_cost
