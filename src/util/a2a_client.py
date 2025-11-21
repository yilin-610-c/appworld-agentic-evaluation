"""A2A client utilities for communicating between agents."""
import httpx
import asyncio
import uuid

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    Part,
    TextPart,
    MessageSendParams,
    Message,
    Role,
    SendMessageRequest,
    SendMessageResponse,
)


async def get_agent_card(url: str) -> AgentCard | None:
    """Get the agent card from an A2A agent URL."""
    httpx_client = httpx.AsyncClient()
    resolver = A2ACardResolver(httpx_client=httpx_client, base_url=url)
    card: AgentCard | None = await resolver.get_agent_card()
    return card


async def wait_agent_ready(url: str, timeout: int = 10) -> bool:
    """Wait until the A2A server is ready by checking the agent card.
    
    Args:
        url: The base URL of the agent
        timeout: Maximum seconds to wait
        
    Returns:
        True if agent is ready, False otherwise
    """
    retry_cnt = 0
    while retry_cnt < timeout:
        retry_cnt += 1
        try:
            card = await get_agent_card(url)
            if card is not None:
                return True
            else:
                print(
                    f"Agent card not available yet, retrying {retry_cnt}/{timeout}"
                )
        except Exception:
            pass
        await asyncio.sleep(1)
    return False


async def send_message(
    url: str, message: str, task_id: str | None = None, context_id: str | None = None
) -> SendMessageResponse:
    """Send a text message to an A2A agent.
    
    Args:
        url: The base URL of the agent
        message: The text message to send
        task_id: Optional task ID for the message
        context_id: Optional context ID for continuing a conversation
        
    Returns:
        The response from the agent
    """
    card = await get_agent_card(url)
    # Increased timeout to 300 seconds (5 minutes) to handle slow API calls and LLM responses
    httpx_client = httpx.AsyncClient(timeout=300.0)
    client = A2AClient(httpx_client=httpx_client, agent_card=card)

    message_id = uuid.uuid4().hex
    params = MessageSendParams(
        message=Message(
            role=Role.user,
            parts=[Part(TextPart(text=message))],
            message_id=message_id,
            task_id=task_id,
            context_id=context_id,
        )
    )
    request_id = uuid.uuid4().hex
    req = SendMessageRequest(id=request_id, params=params)
    response = await client.send_message(request=req)
    return response

