"""Run the MCP server via the ``debug_server`` namespace."""

from client.mcp import (
    DebugServerMCPServer,
    ToolInfo,
    ToolResult,
    ToolStream,
    load_mcp_config,
    main,
    run_stdio_event_loop,
)

__all__ = [
    "DebugServerMCPServer",
    "ToolInfo",
    "ToolResult",
    "ToolStream",
    "load_mcp_config",
    "main",
    "run_stdio_event_loop",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
