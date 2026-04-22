import time
import os
import httpx
from oci_genai_auth import OciInstancePrincipalAuth
from openai import OpenAI

def main() -> None:
    COMPARTMENT_OCID = os.getenv("TF_VAR_compartment_ocid")
    PREFIX = os.getenv("TF_VAR_prefix")
    REGION = os.getenv("TF_VAR_region")
    
    print("<create_vector_store.py>")

    cp_client = OpenAI(
        base_url=f"https://generativeai.{REGION}.oci.oraclecloud.com/20231130/openai/v1",
        api_key="unused",
        http_client=httpx.Client(
            auth=OciInstancePrincipalAuth(),
            headers={
                "opc-compartment-id": COMPARTMENT_OCID,
            },
        ),
    )

    vector_store = cp_client.vector_stores.create(
        name=f"{PREFIX}-vs",
        description=f"{PREFIX} vector store",
        expires_after={"anchor": "last_active_at", "days": 365}, # 1 YEAR ? 
        metadata={"prefix": "{PREFIX}"},
    )

    print(vector_store)
    print(vector_store.id)

    # Create bash file
    with open("responses_env.sh", "w") as f:
        f.write(f'export VECTOR_STORE_ID="{vector_store.id}"\n')

    print("responses_env.sh file created.")
    
    elapsed = 0
    while elapsed < 500:
        vector_store = cp_client.vector_stores.retrieve(vector_store_id)
        if vector_store.status in [ "completed", "failed" ]:
            break
        time.sleep(5)  
        elapsed += 5

    if vector_store.status == "completed":
        print("Vector store created successfully.")
    elif vector_store.status == "failed":
        print("Vector store creation failed.")
    else:
        print("Timeout reached before completion.")
    print(f"Time {elapsed} secs")

if __name__ == "__main__":
    main()
