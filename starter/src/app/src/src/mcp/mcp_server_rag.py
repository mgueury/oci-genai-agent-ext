from fastmcp import FastMCP  # Import FastMCP, the quickstart server base
import shared
import rag_storage
import shared
import pprint

mcp = FastMCP("RAG Server")  # Initialize an MCP server instance with a descriptive name

session_id=None
rag_storage.init()

@mcp.tool()
def search(question: str) -> dict:
    """Search in document."""

    print("<search>", flush=True)
    global session_id
    # Create session
    if not session_id:
        session_id = shared.genai_agent_get_session()
    response = shared.genai_agent_chat(session_id, question)
    source_url = "none"
    if response.message.content.citations:
        source_url = response.message.content.citations[0].source_location.url.replace( " ", "%20" )

    d = {"response": response.message.content.text, "citation": source_url}
    return pprint.pformat(response.message.content)

@mcp.tool()
def get_document_by_path(doc_path: str) -> str:
    """get document by path"""
    print("<get_document_by_path>", flush=True)
    return rag_storage.getDocByPath(doc_path)

if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=9000)
    # print( search( "what is jazz" ) )
    # mcp.run(transport="stdio")  # Run the server, using standard input/output for communication
