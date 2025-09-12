from mcp.server.fastmcp import FastMCP  # Import FastMCP, the quickstart server base
import oci
import os

mcp = FastMCP("RAG Server")  # Initialize an MCP server instance with a descriptive name

signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
config = {'region': signer.region, 'tenancy': signer.tenancy_id}
region = os.getenv("TF_VAR_region")
endpoint = "https://agent-runtime.generativeai."+region+".oci.oraclecloud.com"

genai_agent_runtime_client = oci.generative_ai_agent_runtime.GenerativeAiAgentRuntimeClient(
        config = {}, 
        signer=signer, 
        service_endpoint=endpoint,
        retry_strategy=oci.retry.NoneRetryStrategy(), 
        timeout=(10, 240)
    )
agent_endpoint_id = os.getenv("TF_VAR_agent_endpoint_ocid")

@mcp.tool()  # Register a function as a callable tool for the model
def search(question: string) -> string:
    """Search in document."""
    # Create session
    create_session_details = oci.generative_ai_agent_runtime.models.CreateSessionDetails(
        display_name="display_name", description="description"
    )
    create_session_response = genai_agent_runtime_client.create_session(create_session_details, agent_endpoint_id)    
    session_id = create_session_response.data.id
    chat_details = oci.generative_ai_agent_runtime.models.ChatDetails(
        user_message=str(question), should_stream=False, session_id=session_id  
    )
    execute_session_response = genai_agent_runtime_client.chat(agent_endpoint_id, chat_details)
    if execute_session_response.status == 200:
        if execute_session_response.data.message:
            response_content = execute_session_response.data.message.content
            print( str(response_content), flush=True )                
            return response_content.text
    return "search error"


if __name__ == "__main__":
    mcp.run(transport="stdio")  # Run the server, using standard input/output for communication
