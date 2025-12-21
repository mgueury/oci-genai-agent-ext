"""
MCP server config
"""

MCP_SERVERS_CONFIG = {
    "default": {
        "transport": "streamable_http",
        "url": "http://localhost:2025/mcp/",
    },
    "oci-semantic-search": {
        "transport": "streamable_http",
        "url": "http://localhost:2025/mcp/",
    },
}
