"""Launcher module - initiates and coordinates the evaluation process."""

import multiprocessing
import asyncio
from src.green_agent.agent import start_green_agent
from src.white_agent.agent import start_white_agent
from src.util.a2a_client import wait_agent_ready, send_message


async def launch_evaluation(task_id: str = "82e2fac_1"):
    """Launch the complete evaluation workflow.
    
    Args:
        task_id: AppWorld task ID to evaluate
    """
    # Start green agent
    print("Launching green agent...")
    green_address = ("localhost", 9001)
    green_url = f"http://{green_address[0]}:{green_address[1]}"
    p_green = multiprocessing.Process(
        target=start_green_agent, 
        args=("appworld_green_agent", *green_address)
    )
    p_green.start()
    
    print("Waiting for green agent to be ready...")
    if not await wait_agent_ready(green_url):
        print("Error: Green agent not ready in time")
        p_green.terminate()
        p_green.join()
        return
    print("Green agent is ready.")

    # Start white agent
    print("\nLaunching white agent...")
    white_address = ("localhost", 9002)
    white_url = f"http://{white_address[0]}:{white_address[1]}"
    p_white = multiprocessing.Process(
        target=start_white_agent, 
        args=("appworld_white_agent", *white_address)
    )
    p_white.start()
    
    print("Waiting for white agent to be ready...")
    if not await wait_agent_ready(white_url):
        print("Error: White agent not ready in time")
        p_green.terminate()
        p_green.join()
        p_white.terminate()
        p_white.join()
        return
    print("White agent is ready.")

    # Send the task description to green agent
    print(f"\nSending task to green agent (task_id: {task_id})...")
    task_text = f"""Your task is to test the agent located at:
<white_agent_url>
{white_url}
</white_agent_url>

Using AppWorld task:
<task_id>
{task_id}
</task_id>
"""
    
    print("Task description:")
    print(task_text)
    print("\nSending to green agent...")
    
    try:
        response = await send_message(green_url, task_text)
        print("\n" + "="*80)
        print("Response from green agent:")
        print("="*80)
        print(response)
        print("="*80)
    except Exception as e:
        print(f"Error during evaluation: {e}")
        import traceback
        traceback.print_exc()

    print("\nEvaluation complete. Terminating agents...")
    p_green.terminate()
    p_green.join()
    p_white.terminate()
    p_white.join()
    print("Agents terminated.")


