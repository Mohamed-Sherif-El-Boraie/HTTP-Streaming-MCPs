# Import necessary libraries and modules
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import traceback
from loguru import logger
from typing import Optional, List, Dict, Any

from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient
from mem0 import MemoryClient

from configs.config import TAVILY_API_KEY, MEM0_API_KEY, MEM0_ORG_ID, MEM0_PROJECT_ID




# MCP Server Initialization
mcp = FastMCP("Memoria", stateless_http=False)

# Tavily Search Client Setup
def get_search_client() -> TavilyClient:
    api_key = TAVILY_API_KEY
    if not api_key:
        raise EnvironmentError("TAVILY_API_KEY is missing.")
    return TavilyClient(api_key=api_key)

search_client = get_search_client()


memory_client = MemoryClient(
    api_key    = MEM0_API_KEY,
    org_id     = MEM0_ORG_ID,
    project_id = MEM0_PROJECT_ID
)

#  Web Search Tool
@mcp.tool()
def web_search(query: str) -> Any:
    """
    Perform a web search using the Tavily API.

    Args:
        query: The search query string.

    Returns:
        The search results or an error message.
    """
    try:
        results = search_client.search(query)
        return results or "No results found."
    except Exception as e:
        logger.error(f"web_search error: {e}")
        logger.debug(traceback.format_exc())
        return f"Search failed: {e}"


# Memory Tools (Short-term and Long-term)
@mcp.tool()
def add_short_memory(
    messages: List[Dict[str, str]],
    user_id: str,
    run_id: str,
    async_mode: bool = True
) -> str:
    """
    Store a sequence of messages as short-term memory for this session.
    
    Args:
        messages:   A list of {"role": "...", "content": "..."} dicts for this chat turn.
        user_id:    Stable human identifier (e.g. "alice").
        run_id:     Unique session identifier to mark these facts as ephemeral (e.g. "football").
        async_mode: If True, returns immediately and processes in background.
    """
    try:
        memory_client.add(
            messages   = messages,
            user_id    = user_id,
            run_id     = run_id,
            version    = "v2",
            async_mode = async_mode
        )
        mode = "async" if async_mode else "sync"
        return f"Episodic memory ({mode}) scheduled for user={user_id}, run_id={run_id}"
    except Exception as e:
        logger.error(f"add_episodic_memory error: {e}")
        logger.debug(traceback.format_exc())
        return f"Failed to add episodic memory: {e}"

@mcp.tool()
def add_longterm_memory(
    messages: List[Dict[str, str]],
    user_id: str,
    agent_id: Optional[str] = None,
    async_mode: bool = True
) -> str:
    """
    Use this tool to persist key metadata, preferences, and critical facts long-term.
    
    Args:
        messages:   A list of {"role": "...", "content": "..."} dicts to persist.
        user_id:    Stable human identifier (e.g. "alice").
        agent_id:   Optional stable bot identifier (e.g. "agent-1").
        async_mode: If True, returns immediately and processes in background.
    """
    try:
        memory_client.add(
            messages   = messages,
            user_id    = user_id,
            agent_id   = agent_id,
            version    = "v2",
            async_mode = async_mode
        )
        mode = "async" if async_mode else "sync"
        tag = f"user={user_id}" + (f", agent={agent_id}" if agent_id else "")
        return f"Long-term memory ({mode}) scheduled for {tag}"
    except Exception as e:
        logger.error(f"add_longterm_memory error: {e}")
        logger.debug(traceback.format_exc())
        return f"Failed to add long-term memory: {e}"

# Memory Retrieval & Management Tools

@mcp.tool()
def search_memories_v2(
    query: str,
    filters: Dict[str, Any]
) -> Any:
    """
    Perform a semantic search over stored memories.

    Args:
        query:   The natural-language search query.
        filters: Allowing for more precise memory retrieval. It supports complex logical operations (AND, OR, NOT) and comparison operators for advanced filtering capabilities. The comparison operators include:
                - in: Matches any of the values specified
                - gte: Greater than or equal to
                - lte: Less than or equal to
                - gt: Greater than
                - lt: Less than
                - ne: Not equal to
                - icontains: Case-insensitive containment check
                - *: Wildcard character that matches everything

    Returns:
        Search results or an error message.
    """
    try:
        return memory_client.search(
            query   = query,
            version = "v2",
            filters = filters
        )
    except Exception as e:
        logger.error(f"search_memories_v2 error: {e}")
        logger.debug(traceback.format_exc())
        return f"Search v2 failed: {e}"

@mcp.tool()
def get_memories(user_id: str) -> Any:
    """
    Retrieves all memories associated with a specific user_id.
    Call this at the start of a session to understand the user's history.

    Args:
        user_id: The stable identifier for the user (e.g., "Sherif").

    Returns:
        A list of matching memory objects or an empty list if none are found.
    """
    if not user_id:
        return "Error: user_id cannot be empty."
    try:
        # We construct the filter correctly here, so the model doesn't have to.
        filters = {"user_id": user_id}
        logger.info(f"🔍 Getting memories with filter: {filters}")
        
        memories = memory_client.get_all(
            filters=filters,
            version="v2"
        )
        return memories or [] # Always return a list, even if it's empty.
    
    except Exception as e:
        logger.error(f"get_memories error: {e}")
        logger.debug(traceback.format_exc())
        return f"Retrieving memories failed: {e}"

@mcp.tool()
def memory_history(memory_id: str) -> Any:
    """
    Fetch the full edit history of a single memory.

    Args:
        memory_id: The unique identifier of the memory to inspect.

    Returns:
        A list of historical versions or an error message.
    """
    try:
        return memory_client.history(memory_id=memory_id)
    except Exception as e:
        logger.error(f"memory_history error: {e}")
        logger.debug(traceback.format_exc())
        return f"History lookup failed: {e}"

@mcp.tool()
def get_memory(memory_id: str) -> Any:
    """
    Retrieve a single memory by its ID.

    Args:
        memory_id: The unique identifier of the memory.

    Returns:
        The memory object or an error message.
    """
    try:
        return memory_client.get(memory_id=memory_id)
    except Exception as e:
        logger.error(f"get_memory error: {e}")
        logger.debug(traceback.format_exc())
        return f"Retrieving memory failed: {e}"

@mcp.tool()
def update_memory(
    memory_id: str,
    text: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Update the content or metadata of an existing memory.

    Args:
        memory_id: The ID of the memory to update.
        text:      New text content (optional).
        metadata:  Additional metadata fields (optional).

    Returns:
        The updated memory object or an error message.
    """
    try:
        return memory_client.update(
            memory_id = memory_id,
            text      = text,
            metadata  = metadata
        )
    except Exception as e:
        logger.error(f"update_memory error: {e}")
        logger.debug(traceback.format_exc())
        return f"Updating memory failed: {e}"

@mcp.tool()
def delete_memory(memory_id: str) -> Any:
    """
    Delete a memory entry by its ID.

    Args:
        memory_id: The ID of the memory to delete.

    Returns:
        A confirmation of deletion or an error message.
    """
    try:
        return memory_client.delete(memory_id=memory_id)
    except Exception as e:
        logger.error(f"delete_memory error: {e}")
        logger.debug(traceback.format_exc())
        return f"Deleting memory failed: {e}"


if __name__ == "__main__":
    try:
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.debug(traceback.format_exc())
