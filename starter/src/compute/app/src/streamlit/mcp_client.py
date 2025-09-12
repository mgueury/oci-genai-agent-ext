import streamlit as st
import subprocess
import json
import threading
import queue
import time
import re
import sys

# --- Constants ---
MCP_SERVER_SCRIPT = "mcp_server.py"
# Use the same python executable that is running Streamlit to avoid version conflicts
PYTHON_EXECUTABLE = sys.executable

# --- Mock LLM ---
def LLM(question, tools):
    """
    A mock LLM that decides whether to call a tool or respond with text.
    It uses simple regex matching to detect tool calls and extract arguments.
    """
    question_lower = question.lower()

    # Pattern to call the 'get_weather' tool
    # Example: "what is the weather in new york?"
    weather_match = re.search(r"weather in ([\w\s]+)", question_lower)
    if weather_match:
        location = weather_match.group(1).strip()
        return {
            "tool_call": {"name": "get_weather", "arguments": {"location": location}},
            "thought": f"The user is asking for the weather in '{location}'. I should use the `get_weather` tool."
        }

    # Pattern to call the 'send_email' tool
    # Example: "email to me@test.com with subject 'Hi' and body 'Test message'"
    email_match = re.search(r"email\s+to\s+(\S+)\s+with\s+subject\s+['\"](.+?)['\"]\s+and\s+body\s+['\"](.+?)['\"]", question_lower)
    if email_match:
        recipient, subject, body = email_match.groups()
        return {
            "tool_call": {"name": "send_email", "arguments": {"recipient": recipient, "subject": subject, "body": body}},
            "thought": f"The user wants to send an email to {recipient}. I should use the `send_email` tool."
        }

    # Default text response if no tool is matched
    return {
        "text_response": "I'm not sure how to help with that. Try asking for the weather or to send an email. For example: 'What is the weather in London?'",
        "thought": "I couldn't match the user's request to any available tools, so I'll provide a helpful message."
    }

# --- MCP Client Class ---
class MCPClient:
    """Manages the MCP server subprocess and communication."""
    def __init__(self):
        self._process = None
        self._reader_thread = None
        self._response_queue = queue.Queue()
        self._request_id_counter = 0

    def start_server(self):
        """Starts the MCP server as a subprocess if it's not already running."""
        if self._process and self._process.poll() is None:
            return
        try:
            self._process = subprocess.Popen(
                [PYTHON_EXECUTABLE, MCP_SERVER_SCRIPT],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1
            )
            self._reader_thread = threading.Thread(target=self._enqueue_output, daemon=True)
            self._reader_thread.start()
        except FileNotFoundError:
            st.error(f"MCP Server script not found. Make sure '{MCP_SERVER_SCRIPT}' is in the same directory.")
            st.stop()
        except Exception as e:
            st.error(f"Failed to start MCP server: {e}")
            st.stop()

    def _enqueue_output(self):
        """Reads lines from the server's stdout and stderr and puts them in a queue."""
        for line in iter(self._process.stdout.readline, ''):
            self._response_queue.put(("stdout", line))
        for line in iter(self._process.stderr.readline, ''):
            self._response_queue.put(("stderr", line))

    def _send_request(self, method, params=None):
        """Sends a JSON-RPC request to the server."""
        if not self._process or self._process.poll() is not None:
             st.error("MCP Server is not running.")
             return None
        self._request_id_counter += 1
        request = {"jsonrpc": "2.0", "method": method, "id": self._request_id_counter}
        if params:
            request["params"] = params
        self._process.stdin.write(json.dumps(request) + '\n')
        self._process.stdin.flush()
        return self._request_id_counter

    def _get_response(self, request_id, timeout=5):
        """Retrieves a response for a specific request ID from the queue."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                source, line = self._response_queue.get(timeout=0.1)
                if source == "stderr":
                    st.warning(f"MCP Server Error: {line.strip()}")
                    continue
                response = json.loads(line)
                if response.get("id") == request_id:
                    return response
            except queue.Empty:
                continue
            except (json.JSONDecodeError, AttributeError):
                st.warning(f"Could not decode JSON from server: {line}")
        return None

    def list_tools(self):
        req_id = self._send_request("mcp.list_tools")
        if req_id:
            response = self._get_response(req_id)
            return response.get("result", []) if response else []
        return []

    def call_tool(self, name, arguments):
        params = {"name": name, "arguments": arguments}
        req_id = self._send_request("mcp.call_tool", params)
        if req_id:
            response = self._get_response(req_id)
            return response.get("result", {"error": "No result found in response."}) if response else {"error": "Timeout or no response from server."}

# --- Streamlit App UI ---
st.set_page_config(page_title="MCP Tool-Calling Agent", layout="wide")
st.title("🤖 MCP Tool-Calling Agent")
st.caption("An interface to interact with an LLM that can use tools from an MCP server.")

# Initialize session state for client, tools, and messages
if 'mcp_client' not in st.session_state:
    st.session_state.mcp_client = MCPClient()
    st.session_state.mcp_client.start_server()
    time.sleep(0.5) # Give server a moment to start
if 'tools' not in st.session_state:
    with st.spinner("Fetching tools from MCP server..."):
        st.session_state.tools = st.session_state.mcp_client.list_tools()
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Sidebar to display available tools
with st.sidebar:
    st.header("🛠️ Available Tools")
    if st.session_state.tools:
        for tool in st.session_state.tools:
            with st.expander(f"`{tool['name']}`"):
                st.write(tool['description'])
                if tool.get('parameters'):
                    st.write("**Parameters:**")
                    for param in tool['parameters']:
                        req = " (required)" if param.get('required') else ""
                        st.markdown(f"- `{param['name']}`: {param['description']}{req}")
    else:
        st.warning("No tools found or server not responding.")
    if st.button("🔄 Refresh Tools"):
        st.session_state.tools = st.session_state.mcp_client.list_tools()
        st.rerun()

# Main Chat Interface
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What would you like to do?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            llm_response = LLM(prompt, st.session_state.tools)
            
            if "thought" in llm_response:
                st.info(f"**Thought:** {llm_response['thought']}")

            if "tool_call" in llm_response:
                tool_call = llm_response["tool_call"]
                tool_name, tool_args = tool_call["name"], tool_call["arguments"]
                call_msg = f"Calling tool `{tool_name}` with arguments: `{tool_args}`"
                st.markdown(call_msg)
                st.session_state.messages.append({"role": "assistant", "content": call_msg})
                
                tool_result = st.session_state.mcp_client.call_tool(tool_name, tool_args)
                result_msg = f"**Tool Result:**\n```\n{json.dumps(tool_result, indent=2)}\n```"
                st.markdown(result_msg)
                st.session_state.messages.append({"role": "assistant", "content": result_msg})

            elif "text_response" in llm_response:
                response_text = llm_response["text_response"]
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
