from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
import os
import time
from langchain_oci import ChatOCIGenAI

COMPARTMENT_OCID = os.getenv("TF_VAR_compartment_ocid")
OPENAI_BASE_URL = os.getenv("TF_VAR_openai_base_url")
OPENAI_MODEL = os.getenv("TF_VAR_openai_model")
OPENAI_API_KEY = os.getenv("TF_VAR_openai_api_key")

# llm = ChatOpenAI(
#     model=OPENAI_MODEL, # LLM_MODEL_ID,  # for example "xai.grok-4-fast-reasoning"
#     api_key=OPENAI_API_KEY,
#     base_url=OPENAI_BASE_URL,
#     stream_usage=True,
# )

llm = ChatOCIGenAI(
    auth_type="INSTANCE_PRINCIPAL",
    model_id="xai.grok-4-fast-reasoning",
    service_endpoint="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com",
    compartment_id=COMPARTMENT_OCID,
    is_stream=True,
    model_kwargs={"temperature": 0}
)

async def init() -> StateGraph:

    # Waiting is important, since after reboot the MCP server could start afterwards.
    delay = 5
    for attempt in range(1, 10):
        try:
            print(f"Connecting to MCP {attempt}...")
            client = MultiServerMCPClient(
                {
                    "Documents": {
                        "transport": "streamable_http",
                        "url": "http://localhost:9000/mcp"
                    },
                }
            )
            tools = await client.get_tools()
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
        tools=tools,
        prompt=(
            "You are a research agent.\n\n"
            "INSTRUCTIONS:\n"
            "- Assist ONLY with research-related tasks, DO NOT do any math\n"
            "- Respond ONLY with the results of your work, do NOT include ANY other text."
        ),
        name="research_agent", 
    ) 
    return agent

agent = asyncio.run(init())
