
from langchain_openai import ChatOpenAI
import httpx
import oci_openai 
import os
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import convert_to_messages
from fastapi import FastAPI
from langserve import add_routes
import uvicorn
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage
import pprint

def inp(question: str) -> dict:
    return {"messages": [{"role": "user", "content": question}]}

def out(state: dict):
    pprint.pprint( state )
    # {'agent': {'messages': [AIMessage(content='Jazz is a music genre that originated in the African-American communities of New Orleans, Louisiana, in the late 19th and early 20th centuries, with its roots in blues and ragtime. It is characterized by swing and blue notes, complex chords, call and response vocals, polyrhythms, and improvisation, and has roots in European harmony and African rhythmic rituals. Since the 1920s Jazz Age, it has been recognized as a major form of musical expression in traditional and popular music.', additional_kwargs={}, response_metadata={'finish_reason': 'stopstop', 'model_name': 'xai.grok-4-fast-reasoning'}, name='research_agent', id='lc_run--f62513db-ad32-4aef-a4ad-7967cbd5dd17', usage_metadata={'input_tokens': 239, 'output_tokens': 105, 'total_tokens': 344, 'input_token_details': {}, 'output_token_details': {'reasoning': 0}})]}}
    result = state["agent"]["messages"][0]
    return result

def wrap_input(message: HumanMessage):
    return {"messages": [message]}

COMPARTMENT_ID = os.getenv("TF_VAR_compartment_ocid")
REGION = os.getenv("TF_VAR_region")
LLM_MODEL_ID = os.getenv("TF_VAR_genai_meta_model")
EMBED_MODEL_ID=os.getenv("TF_VAR_genai_embed_model")
OPENAI_BASE_URL = os.getenv("TF_VAR_openai_base_url")
OPENAI_MODEL = os.getenv("TF_VAR_openai_model")
OPENAI_API_KEY = os.getenv("TF_VAR_openai_api_key")

auth = oci_openai.OciInstancePrincipalAuth()
# auth = oci_openai.OciUserPrincipalAuth(profile_name="DEFAULT")

llm = ChatOpenAI(
    model=OPENAI_MODEL, # LLM_MODEL_ID,  # for example "xai.grok-4-fast-reasoning"
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
    stream_usage=True,
)

# llm = ChatOpenAI(
#     model="xai.grok-4-fast-reasoning", # LLM_MODEL_ID,  # for example "xai.grok-4-fast-reasoning"
#     api_key="OCI",
#     base_url="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/v1",
#     http_client=httpx.Client(
#         auth=auth,
#         headers={"CompartmentId": COMPARTMENT_ID}
#     ), 
#     stream_usage=True,
# )

def pretty_print_message(message, indent=False):
    pretty_message = message.pretty_repr(html=True)
    if not indent:
        print(pretty_message)
        return

    indented = "\n".join("\t" + c for c in pretty_message.split("\n"))
    print(indented)

def pretty_print_messages(update, last_message=False):
    is_subgraph = False
    if isinstance(update, tuple):
        ns, update = update
        # skip parent graph updates in the printouts
        if len(ns) == 0:
            return

        graph_id = ns[-1].split(":")[0]
        print(f"Update from subgraph {graph_id}:")
        print("\n")
        is_subgraph = True

    for node_name, node_update in update.items():
        update_label = f"Update from node {node_name}:"
        if is_subgraph:
            update_label = "\t" + update_label

        print(update_label)
        print("\n")

        messages = convert_to_messages(node_update["messages"])
        if last_message:
            messages = messages[-1:]

        for m in messages:
            pretty_print_message(m, indent=is_subgraph)
        print("\n")
   
# Initialize the OpenAI LLM
# We use gpt-4o-mini for better tool-calling and speed, but you can change it.

async def init(app):
    client = MultiServerMCPClient(
        {
            "math": {
                "transport": "streamable_http",
                "url": "http://localhost:9000/mcp"
            },
        }
    )
    tools = await client.get_tools()
    research_agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=(
            "You are a research agent.\n\n"
            "INSTRUCTIONS:\n"
            "- Assist ONLY with research-related tasks, DO NOT do any math\n"
            "- After you're done with your tasks, respond to the supervisor directly\n"
            "- Respond ONLY with the results of your work, do NOT include ANY other text."
        ),
        name="research_agent",
    ) 
    # async for chunk in research_agent.astream(
    #     {"messages": [{"role": "user", "content": "what is jazz ?"}]}
    # ):
    #     pretty_print_messages(chunk)    
  
    wrap_agent = RunnableLambda(inp) | research_agent | RunnableLambda(out)

    add_routes(
        app,
        wrap_agent,
        path="/agent",  # <- This path '/agent' is your Graph ID
        playground_type="default",
    )

if __name__ == "__main__":
    app = FastAPI(title="LangGraph Agent Server")
    asyncio.run(init(app))
    uvicorn.run(app, host="0.0.0.0", port=8080)    
