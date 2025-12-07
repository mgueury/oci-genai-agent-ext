from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
import os

OPENAI_BASE_URL = os.getenv("TF_VAR_openai_base_url")
OPENAI_MODEL = os.getenv("TF_VAR_openai_model")
OPENAI_API_KEY = os.getenv("TF_VAR_openai_api_key")

llm = ChatOpenAI(
    model=OPENAI_MODEL, # LLM_MODEL_ID,  # for example "xai.grok-4-fast-reasoning"
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
    stream_usage=True,
)

async def init() -> StateGraph:
    client = MultiServerMCPClient(
        {
            "Documents": {
                "transport": "streamable_http",
                "url": "http://localhost:9000/mcp"
            },
        }
    )
    tools = await client.get_tools()
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
