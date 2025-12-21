from fastmcp import FastMCP  # Import FastMCP, the quickstart server base
import shared
import rag_storage
import shared
import pprint
from typing import List, TypedDict
from pydantic import BaseModel

mcp = FastMCP("MCP RAG Server")  # Initialize an MCP server instance with a descriptive name

rag_storage.init()

class DocInfo(BaseModel):
    TITLE: str
    PATH: str

@mcp.tool()
def search(question: str) -> dict:
    """Search in document."""
    print("<search>", flush=True)
    # Create session
    session_id = shared.genai_agent_get_session()
    response = shared.genai_agent_chat(session_id, question)
    source_url = "none"
    if response.message.content.citations:
        source_url = response.message.content.citations[0].source_location.url.replace( " ", "%20" )

    d = {"response": response.message.content.text, "citation": source_url}
    pprint.pprint(d)
    return d

@mcp.tool()
def list_documents() ->  List[DocInfo]:
    """get the list of documents. Return for each document (PATH, TITLE)"""
    print("<list_documents>", flush=True)
    return rag_storage.getDocList()

@mcp.tool()
def get_document_summary(doc_path: str) -> dict:
    """get document summary by path"""
    print("<get_document_summary>", flush=True)
    return rag_storage.getDocByPath(doc_path)

@mcp.tool()
def get_document_by_path(doc_path: str) -> dict:
    """get document by path"""
    print("<get_document_by_path>", flush=True)
    return rag_storage.getDocByPath(doc_path)

@mcp.tool()
def find_service_request(question: str) -> List[dict]:
    """find similar service requests"""
    print("<find_service_request>", flush=True)
    return rag_storage.findServiceRequest(question)

@mcp.tool()
def get_service_request(id: str) -> dict:
    """get the service request details"""
    print("<get_service_request>", flush=True)
    return rag_storage.getServiceRequest(id)


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=2025)
    # print( search( "what is jazz" ) )
    # mcp.run(transport="stdio")  # Run the server, using standard input/output for communication
