from langchain_openai import ChatOpenAI
import httpx
import oci_openai 
import os
import asyncio

COMPARTMENT_ID = os.getenv("TF_VAR_compartment_ocid")
auth = oci_openai.OciInstancePrincipalAuth()

print('-- LangChain INVOKE --------------------------------------------------------')

llm = ChatOpenAI(
    model="xai.grok-4-fast-reasoning",
    api_key="OCI",
    base_url="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/v1",
    http_client=httpx.Client(
        auth=auth,
        headers={"CompartmentId": COMPARTMENT_ID}
    ),
)

async def test():
    messages = [
        (
            "system",
            "You are a helpful assistant that translates English to French. Translate the user sentence.",
        ),
        ("human", "I love programming."),
    ]
    ai_msg = llm.invoke(messages)
    print(ai_msg)

    print('-- LangChain AINVOKE --------------------------------------------------------')

    ai_msg = await llm.ainvoke(messages)
    print(ai_msg)

asyncio.run(test())
