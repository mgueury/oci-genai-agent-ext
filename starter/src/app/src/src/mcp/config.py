"""
File name: config.py
Author: Luigi Saetta
Date last modified: 2025-07-02
Python Version: 3.11

Description:
    This module provides general configurations


Usage:
    Import this module into other scripts to use its functions.
    Example:
        import config

License:
    This code is released under the MIT License.

Notes:
    This is a part of a demo showing how to implement an advanced
    RAG solution as a LangGraph agent.

Warnings:
    This module is in development, may change in future versions.
"""

import os

DEBUG = False

# type of auth
AUTH = "INSTANCE_PRINCIPAL"

# LLM
# this is the default model
LLM_MODEL_ID = os.getenv("TF_VAR_genai_meta_model")
EMBED_MODEL_ID=os.getenv("TF_VAR_genai_embed_model")
NVIDIA_EMBED_MODEL_URL="-"
TEMPERATURE = 0.1
MAX_TOKENS = 4000

# OCI general
REGION = os.getenv("TF_VAR_region")
COMPARTMENT_ID = os.getenv("TF_VAR_compartment_ocid")
SERVICE_ENDPOINT = f"https://inference.generativeai.{REGION}.oci.oraclecloud.com"

# for the UI
LANGUAGE_LIST = ["same as the question", "en", "fr", "it", "es"]
# replaced command-r with command-a

if REGION == "us-chicago-1":
    # for now only available in chicago region
    MODEL_LIST = [
        "xai.grok-3",
        "xai.grok-4",
        "openai.gpt-4.1",
        "openai.gpt-4o",
        "openai.gpt-5",
        "meta.llama-3.3-70b-instruct",
        "cohere.command-a-03-2025",
    ]
else:
    MODEL_LIST = [
        "meta.llama-3.3-70b-instruct",
        "cohere.command-a-03-2025",
        "openai.gpt-4.1",
        "openai.gpt-4o",
        "openai.gpt-5",
    ]

# for MCP server
TRANSPORT = "streamable-http"
HOST = "0.0.0.0"
PORT = 9000

# with this we can toggle JWT token auth
ENABLE_JWT_TOKEN = False
# for JWT token with OCI
IAM_BASE_URL = "https://idcs-xxxxx.identity.oraclecloud.com"
# these are used during the verification of the token
ISSUER = "https://identity.oraclecloud.com/"
AUDIENCE = ["urn:opc:lbaas:logicalguid=idcs-xxxxxxxx"]
