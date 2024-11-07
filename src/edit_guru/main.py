import click
import logzero
import pandas as pd
from rich.console import Console
from rich.markdown import Markdown
from rich.status import Status
from supersullytools.llm.agent import ChatAgent
from supersullytools.llm.completions import CompletionHandler
from supersullytools.llm.trackers import CompletionTracker, SessionUsageTracking

from .agents.ai_developer import ai_developer_agent

package_version = "0.1.2"

# Create a logger instance
logger = logzero.setup_logger(level=logzero.ERROR)


@click.command("main")
@click.argument("task")
@click.option("--approve", is_flag=True, help="Pre-approve the generated plan and automatically execute.")
@click.option("--approve-tools", is_flag=True, help="Pre-approve all tool usage.")
@click.option("-f", is_flag=True, help="Shortcut for --approve and --approve-tools")
def main(task: str, approve: bool, approve_tools: bool, f):
    if f:
        approve = True
        approve_tools = True
    session_tracker = SessionUsageTracking()
    trackers = [session_tracker]
    completion_handler = get_completion_handler(trackers)
    action_agent = ai_developer_agent(logger=logger, completion_handler=completion_handler, max_tool_calls=10)
    plan_agent = ai_developer_agent(logger=logger, completion_handler=completion_handler, max_tool_calls=0)
    action_agent.replace_user_preferences(
        [
            "I can only see your final message after the task is complete, "
            "so be sure you provide a complete answer without assuming I can read your previous messages",
            "Do not make personal judgements about the content or the system you are interacting with; I do "
            "not need to know if you think the repo is a compelling resource, for example. Just stick to the facts.",
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
        confirm_next_loop = False

        if action_agent.get_pending_tool_calls():
            action_agent.approve_pending_tool_usage()

        run_agent_with_status(action_agent, console)

        # for msg in action_agent.chat_history[starting_chat_len:]:
        #     if msg.role == "assistant":
        #         md = Markdown(msg.content)
        #         console.print(msg.role)
        #         console.print(md)
        # starting_chat_len = len(action_agent.chat_history)

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
            click.echo(f"Completions Made: {total_count}")
            click.echo(f"Completions Cost: {total_cost}")
            user_msg = input("Respond to llm (blank line to quit): \n").strip()
            if not user_msg:
                break
            action_agent.message_from_user(user_msg)
            confirm_next_loop = True


def run_agent_with_status(agent: ChatAgent, console):
    with Status("[bold green]AI is initializing...[/bold green]", spinner="dots", console=console) as status:
        while agent.working:
            status.update(f"[bold cyan]AI is processing: {agent.get_current_status_msg()}...[/bold cyan]")
            agent.run_agent()

        # When done, update status to indicate completion
        status.update("[bold green]Task complete![/bold green]")


def make_a_plan(agent: ChatAgent, task: str) -> str:
    prompt = (
        "How would you accomplish the following using your given tools; "
        "for now just make a plan and tell me, do not take any action.\n"
        "Please keep your response concise, as it will be shown to me "
        "in a terminal console with limited display size.\n"
        f"<task>\n{task}\n</task>"
    )
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
        enable_bedrock=False,
    )


if __name__ == "__main__":
    main()
