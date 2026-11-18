"""MCP Client wrapper using langchain-mcp-adapters MultiServerMCPClient."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger("vani-mcp-client")


def create_mcp_client(
    *,
    transport: str | None = None,
    server_url: str | None = None,
    server_path: str | Path | None = None,
) -> MultiServerMCPClient:
    """Create and configure a MultiServerMCPClient for VANI interview tools.

    Supports:
        - 'stdio' (default): Spawns the MCP server as a Python child process.
        - 'sse': Connects to an existing HTTP/SSE MCP server instance.
    """
    resolved_transport = (
        transport or os.environ.get("MCP_TRANSPORT", "stdio")
    ).lower().strip()

    if resolved_transport == "sse":
        url = server_url or os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8000/sse")
        logger.info(f"Connecting to VANI MCP server via SSE at {url}")
        return MultiServerMCPClient(
            connections={
                "vani": {
                    "transport": "sse",
                    "url": url,
                }
            }
        )

    # stdio transport (default)
    resolved_server_path = (
        Path(server_path).resolve()
        if server_path
        else (Path(__file__).resolve().parent.parent / "mcp_server" / "server.py").resolve()
    )

    if not resolved_server_path.exists():
        raise FileNotFoundError(f"MCP server script not found at {resolved_server_path}")

    logger.info(f"Starting VANI MCP server via stdio: {resolved_server_path}")
    return MultiServerMCPClient(
        connections={
            "vani": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(resolved_server_path), "--transport", "stdio"],
                "cwd": str(resolved_server_path.parent),
            }
        }
    )


async def load_vani_tools(
    client: MultiServerMCPClient | None = None,
) -> tuple[MultiServerMCPClient, list[BaseTool]]:
    """Initialize client and retrieve the VANI MCP tools.

    Returns:
        tuple[MultiServerMCPClient, list[BaseTool]]: The client and discovered tools.
    """
    mcp_client = client or create_mcp_client()
    tools = await mcp_client.get_tools()
    logger.info(f"Loaded {len(tools)} MCP tools: {[t.name for t in tools]}")
    return mcp_client, tools
