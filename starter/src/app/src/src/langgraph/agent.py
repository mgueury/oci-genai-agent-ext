from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
import asyncio
import os
import time
from langchain_oci import ChatOCIGenAI
import pprint

COMPARTMENT_OCID = os.getenv("TF_VAR_compartment_ocid")
OPENAI_BASE_URL = os.getenv("TF_VAR_openai_base_url")
OPENAI_MODEL = os.getenv("TF_VAR_openai_model")
OPENAI_API_KEY = os.getenv("TF_VAR_openai_api_key")
REGION = os.getenv("TF_VAR_region")

# llm = ChatOpenAI(
#     model=OPENAI_MODEL, # LLM_MODEL_ID,  # for example "xai.grok-4-fast-reasoning"
#     api_key=OPENAI_API_KEY,
#     base_url=OPENAI_BASE_URL,
#     stream_usage=True,
# )

llm = ChatOCIGenAI(
    auth_type="INSTANCE_PRINCIPAL",
#     model_id="openai.gpt-oss-120b",
#    service_endpoint="https://inference.generativeai."+REGION+".oci.oraclecloud.com",
    model_id="xai.grok-4-fast-reasoning",
    service_endpoint="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com",
    compartment_id=COMPARTMENT_OCID,
    is_stream=True,
    model_kwargs={"temperature": 0}
)

# See https://docs.langchain.com/oss/python/langchain/mcp#accessing-runtime-context
async def inject_user_context(
    request: MCPToolCallRequest,
    handler,
):
    """Inject user credentials into MCP tool calls."""
    print( "--- request ----" )
    pprint( request )
    runtime = request.runtime
    user_id = runtime.context.user_id  
    print( f"user_id={user_id}", flush=True )

    # Add user context to tool arguments
    modified_request = request.override(
        args={**request.args, "user_id": user_id}
    )
    return await handler(modified_request)

async def init( prompt, tools_list, callback_handler=None ) -> StateGraph:

    # Waiting is important, since after reboot the MCP server could start afterwards.
    delay = 5
    for attempt in range(1, 10):
        try:
            print(f"Connecting to MCP {attempt}...")
            client = MultiServerMCPClient(
                {
                    "McpServerRag": {
                        "transport": "streamable_http",
                        "url": "http://localhost:2025/mcp",                     
                    },
                },
                tool_interceptors=[inject_user_context],
            )
            tools = await client.get_tools()
            print( "-- tools ------------------------------------------------------------")
            pprint.pprint( tools )
            # Filter tools.
            tools_filtered = []
            for tool in tools:
                if tool.name in tools_list:
                    tools_filtered.append( tool )
            print( "-- tools_filtered ---------------------------------------------------")
            pprint.pprint( tools_filtered )
            break
        except Exception as e:
            print(f"Connection failed {attempt}: {e}")            
            print(f"Waiting for {delay} seconds before the next attempt...")
            time.sleep(delay)

    if client==None:
        print("ERROR: connection to MCP Failed")
        exit(1)

    agent = create_react_agent(
        model=llm,
        tools=tools_filtered,
        prompt=prompt,
        name="research_agent"
    ) 

    return agent

agent_rag = asyncio.run(init((
            "You are a research agent.\n\n"
            "INSTRUCTIONS:\n"
            "- Assist ONLY with research-related tasks, DO NOT do any math\n"
            "- Respond ONLY with the results of your work, do NOT include ANY other text."
            ),
            ["search","list_documents","get_document_summary","get_document_by_path"]))

prompt_sr = """You are a support agent.
            INSTRUCTIONS:
            - When you receive a question, search the answer by calling the tools search and the tool find_service_request
            - Combine the response of the 2 tools to create a final answer to the user or several possible answers found in the different documents.
            - Answer only based on the result of the tools used. Do not add any other response or content that is not in the result of the tools.
            
            REFERENCES:
            - When you answer always give the list of document on which you based your response. Give this in a table format. 2 columns.
            - One line for each reference found in 
               - For the tool search. Give the document path and content.
               - For the tool find_service_request. Give the link to the SR and the question.   
            Ex:
            | Link | Text |
            | ---- | ---- |                                                                
            | [SR 1](https://url/sr/1) | SR question |                                                                
            | [Document Name](https://document_url/) | Document content |                                                                
            """

agent_sr = asyncio.run(init(prompt_sr,
            ["search","find_service_request","get_service_request"]))



        # prompt=(
        #     "You are a research agent.\n\n"
        #     "INSTRUCTIONS:\n"
        #     "- Assist ONLY with research-related tasks, DO NOT do any math\n"
        #     "- Respond ONLY with the results of your work, do NOT include ANY other text."
        # ),
