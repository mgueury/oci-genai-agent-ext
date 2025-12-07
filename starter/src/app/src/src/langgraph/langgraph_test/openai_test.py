from langchain_openai import ChatOpenAI
import httpx
import oci_openai 
import os
import asyncio

COMPARTMENT_ID = os.getenv("TF_VAR_compartment_ocid")
REGION = os.getenv("TF_VAR_region")
LLM_MODEL_ID = os.getenv("TF_VAR_genai_meta_model")
EMBED_MODEL_ID=os.getenv("TF_VAR_genai_embed_model")

auth = oci_openai.OciInstancePrincipalAuth()
# auth = oci_openai.OciUserPrincipalAuth(profile_name="DEFAULT")

from oci_openai import OciOpenAI, OciSessionAuth
from openai import OpenAI

client = OciOpenAI(
    base_url="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/v1",
    auth=auth,
    compartment_id=COMPARTMENT_ID,
)

completion = client.chat.completions.create(
    model=LLM_MODEL_ID,
    messages=[
        {
            "role": "user",
            "content": "How do I output all files in a directory using Python?",
        },
    ],
)
print(completion.model_dump_json())

print('----------------------------------------------------------')

# Example for OCI Generative AI endpoint
client = OpenAI(
    api_key="OCI",
    base_url="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/v1",
    http_client=httpx.Client(
        auth=auth,
        headers={"CompartmentId": COMPARTMENT_ID}
    ),
)

completion = client.chat.completions.create(
    model=LLM_MODEL_ID,
    messages=[
        {
            "role": "user",
            "content": "How do I output all files in a directory using Python?",
        },
    ],
)
print(completion.model_dump_json())

print('-- LangChain INVOKE --------------------------------------------------------')

llm = ChatOpenAI(
    model=LLM_MODEL_ID,  # for example "xai.grok-4-fast-reasoning"
    api_key="OCI",
    base_url="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/v1",
    http_client=httpx.Client(
        auth=auth,
        headers={"CompartmentId": COMPARTMENT_ID}
    ),
    # use_responses_api=True,
    # stream_usage=False,
    # temperature=None,
    # max_tokens=None,
    # timeout=None,
    # reasoning_effort="low",
    # max_retries=2,
    # other params...
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
