import streamlit as st
import oci
import os
from streamlit_spinner import spinner
import urllib

signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
config = {'region': signer.region, 'tenancy': signer.tenancy_id}
region = os.getenv("TF_VAR_region")
endpoint = "https://agent-runtime.generativeai."+region+".oci.oraclecloud.com"

# Translation dictionary (you can replace this with a file-based solution like JSON or YAML)
translations = {
    "en": {
        "title": "AI Assistant",
        "enter_agent_id": "Enter Agent Endpoint ID",
        "reset_chat": "Reset Chat",
        "reset_chat_help": "Reset chat history and clear screen",
        "type_message": "Type your message here...",
        "error_no_id": "Please enter the Agent Endpoint ID in the sidebar to start the chat.",
        "processing_messages": [
            "Working on your request...",
            "Still processing, please wait...",
            "This might take a little longer...",
            "Almost there, hang tight..."
        ],
        "citations": "Citations",
        "citation": "Citation",
        "source": "Source",
        "selectLang": "Select Language",
        "citation_text": "Citation Text"
    },
    "ro": {
        "title": "Asistent AI",
        "enter_agent_id": "Introduceți ID-ul punctului final al agentului",
        "reset_chat": "Resetați conversația",
        "reset_chat_help": "Resetați istoricul conversațiilor și ștergeți ecranul",
        "type_message": "Scrieți mesajul dvs. aici...",
        "error_no_id": "Vă rugăm să introduceți ID-ul punctului final al agentului în bara laterală pentru a începe conversația",
        "processing_messages": [
            "Lucrăm la solicitarea dvs...",
            "Asistentul AI verifica in documentatie...",
            "Asistentul AI verifica in resurse web...",
            "Aproape am terminat, vă rugăm să așteptați..."
        ],
        "citations": "Citații",
        "citation": "Citația",
        "source": "Sursa",
        "selectLang": "Selectați Limbă",
        "citation_text": "Textul citației"
    }
}

lang_code = "en"
language = st.sidebar.selectbox(translations[lang_code]["selectLang"], options=["English","Romanian"], index=0)
lang_code = "en" if language == "English" else "ro"

st.title(translations[lang_code]["title"])

# Sidebar for agent endpoint ID and reset chat
with st.sidebar:
    agent_endpoint_id = st.text_input(translations[lang_code]["enter_agent_id"], value=os.getenv("TF_VAR_agent_endpoint_ocid"))
    if st.button(translations[lang_code]["reset_chat"], type="primary", use_container_width=True, help=translations[lang_code]["reset_chat_help"]):
        st.session_state.messages = []  
        st.session_state.session_id = None  
        st.rerun()

# Check if agent_endpoint_id is provided
if not agent_endpoint_id:
    st.error(translations[lang_code]["error_no_id"])
else:
    # Initialize session state if not already initialized
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = None

    # Create GenAI Agent Runtime Client (only if session_id is None)
    if st.session_state.session_id is None:

        genai_agent_runtime_client = oci.generative_ai_agent_runtime.GenerativeAiAgentRuntimeClient(
            config = {}, 
            signer=signer,
            service_endpoint=endpoint,
            retry_strategy=oci.retry.NoneRetryStrategy(),
            timeout=(10, 240)
        )

        # Create session
        create_session_details = oci.generative_ai_agent_runtime.models.CreateSessionDetails(
            display_name="display_name", description="description"
        )
        create_session_response = genai_agent_runtime_client.create_session(create_session_details, agent_endpoint_id)

        # Store session ID
        st.session_state.session_id = create_session_response.data.id

        # Check if welcome message exists and append to message history
        if hasattr(create_session_response.data, 'welcome_message'):
            st.session_state.messages.append({"role": "assistant", "content": create_session_response.data.welcome_message})

    # Display chat messages from history (including initial welcome message, if any)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Get user input
    if user_input := st.chat_input(translations[lang_code]["type_message"]):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Execute session (re-use the existing session)
        genai_agent_runtime_client = oci.generative_ai_agent_runtime.GenerativeAiAgentRuntimeClient(
                config = {}, 
                signer=signer, 
                service_endpoint=endpoint,
                retry_strategy=oci.retry.NoneRetryStrategy(), 
                timeout=(10, 240)
            )
        
        # Display a spinner while waiting for the response
        with spinner(translations[lang_code]["processing_messages"]):  # Spinner for visual feedback
            chat_details = oci.generative_ai_agent_runtime.models.ChatDetails(
                user_message=str(user_input), should_stream=False, session_id=st.session_state.session_id  # You can set this to True for streaming responses
            )
            execute_session_response = genai_agent_runtime_client.chat(agent_endpoint_id, chat_details)

        # Display agent response
        if execute_session_response.status == 200:
            response_content = execute_session_response.data.message.content
            st.session_state.messages.append({"role": "assistant", "content": response_content.text})
            with st.chat_message("assistant"):
                st.markdown(response_content.text)
            
            # Display citations
            if response_content.citations:
                with st.expander(translations[lang_code]["citations"]):  # Collapsible section
                    for i, citation in enumerate(response_content.citations, start=1):
                        source_url = citation.source_location.url.replace( " ", "%20" )
                        # st.write(f"**Citation {i}:**")  # Add citation number
                        st.write(f"**{translations[lang_code]['citation']} {i}:**") 
                        st.markdown(f"**{translations[lang_code]['source']}:** [{source_url}]({source_url})") 
                        st.text_area(translations[lang_code]["citation_text"], value=citation.source_text, height=200) # Use st.text_area for better formatting
        else:
            st.error(f"API request failed with status: {execute_session_response.status}")
