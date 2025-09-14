from fastmcp import FastMCP  # Import FastMCP, the quickstart server base
import shared
import rag_storage
import shared

mcp = FastMCP("RAG Server")  # Initialize an MCP server instance with a descriptive name

session_id

@mcp.tool()
def search(question: str) -> str:
    """Search in document."""

    global session_id
    # Create session
    if not session_id:
        session_id = shared.genai_agent_get_session()
    response = shared.genai_agent_chat(session_id, question)
    return response.message.content.text

@mcp.tool()
def get_document_by_path(doc_path: str) -> str:
    """get document by path"""
    return rag_storage.getDocByPath(doc_path)

if __name__ == "__main__":
    mcp.run(transport="stdio")  # Run the server, using standard input/output for communication
