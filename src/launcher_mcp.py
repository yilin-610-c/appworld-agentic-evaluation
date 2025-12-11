"""Launcher module for MCP mode (Approach III)."""

import multiprocessing
import asyncio
import os
from src.green_agent.agent_mcp import start_green_agent_mcp
from src.white_agent.agent_mcp import start_white_agent_mcp
from src.util.a2a_client import wait_agent_ready, send_message


def start_green_agent_process_mcp(host, port):
    start_green_agent_mcp(host=host, port=port)

def start_white_agent_process_mcp(host, port):
    start_white_agent_mcp(host=host, port=port)


async def launch_evaluation_mcp(task_id: str = "82e2fac_1"):
    """Launch the complete evaluation workflow in MCP mode.
    
    Args:
        task_id: AppWorld task ID to evaluate
    """
    # Start green agent
    print("Launching green agent (MCP)...")
    green_port = 9001
    green_url = f"http://localhost:{green_port}"
    p_green = multiprocessing.Process(
        target=start_green_agent_process_mcp, 
        args=("0.0.0.0", green_port)
    )
    p_green.start()
    
    print("Waiting for green agent to be ready...")
    if not await wait_agent_ready(green_url):
        print("Error: Green agent not ready in time")
        p_green.terminate()
        p_green.join()
        return
    print(f"✓ Green Agent (MCP) ready at {green_url}")

    # Start white agent
    print("\nLaunching white agent (MCP)...")
    white_port = 9002
    white_url = f"http://localhost:{white_port}"
    p_white = multiprocessing.Process(
        target=start_white_agent_process_mcp, 
        args=("0.0.0.0", white_port)
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
    print(f"✓ White Agent (MCP) ready at {white_url}")

    # Send the task description to green agent
    print(f"\nSending evaluation request to green agent...")
    print(f"Task: {task_id}")
    print(f"White Agent: {white_url}")
    
    task_text = f"""<white_agent_url>{white_url}</white_agent_url>
<task_id>{task_id}</task_id>
Please evaluate the white agent on this AppWorld task using MCP for tool delivery."""
    
    try:
        # Send initial request to Green Agent
        # Green Agent will then coordinate with White Agent via A2A
        response = await send_message(green_url, task_text)
        
        # The Green Agent will keep running until evaluation is complete
        # We don't need to do anything here, but we should keep the process alive
        # Actually send_message waits for the response, which might take a while if Green Agent
        # completes the whole eval in one request (it does in our implementation)
        
        print("\n" + "="*80)
        print("EVALUATION COMPLETE")
        print("="*80)
        print("Green Agent Response:")
        print(response)
        print("="*80)
        
    except Exception as e:
        print(f"ERROR during evaluation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nShutting down servers...")
        p_green.terminate()
        p_green.join()
        p_white.terminate()
        p_white.join()
        print("✓ Servers stopped")





