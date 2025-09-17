#!/usr/bin/env bash
if [ "$TF_VAR_rag_storage" == "db23ai" ]; then
  # Use the KB of 23ai 
  if [ -f src/terraform/genai_kb_23ai._tf ]; then
    echo "Setting RAG Storage 23ai"
    mv src/terraform/genai_kb_23ai._tf src/terraform/genai_kb_23ai.tf
    mv src/terraform/genai_kb_os.tf src/terraform/genai_kb_os._tf
  fi
fi
