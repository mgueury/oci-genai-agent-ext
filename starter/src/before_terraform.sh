#!/usr/bin/env bash
if [ "$TF_VAR_rag_storage" == "db26ai" ]; then
  # Use the KB of 26ai 
  if [ -f src/terraform/genai_kb_26ai._tf ]; then
    echo "Setting RAG Storage db26ai"
    mv src/terraform/genai_kb_26ai._tf src/terraform/genai_kb_26ai.tf
    mv src/terraform/genai_kb_os.tf src/terraform/genai_kb_os._tf
  fi
fi
