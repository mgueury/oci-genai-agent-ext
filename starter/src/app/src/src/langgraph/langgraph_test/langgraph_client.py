import os
import operator
from typing import TypedDict, Annotated, List, Union
from functools import partial

# LangChain/LangGraph imports
from langchain_openai import ChatOpenAI
from langchain_core import  AgentExecutor
from langchain.agents import create_tool_calling_agent 
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, END

# --- 1. Environment and LLM Setup ---
# NOTE: Ensure OPENAI_API_KEY is set in your environment variables.
# You can set it here for testing if needed: os.environ["OPENAI_API_KEY"] = "your_api_key"

COMPARTMENT_ID = os.getenv("TF_VAR_compartment_ocid")
REGION         = os.getenv("TF_VAR_region")
LLM_MODEL_ID   = os.getenv("TF_VAR_genai_meta_model")
EMBED_MODEL_ID = os.getenv("TF_VAR_genai_embed_model")

# Initialize the OpenAI LLM
# We use gpt-4o-mini for better tool-calling and speed, but you can change it.
llm = ChatOpenAI(
    model=LLM_MODEL_ID,  # for example "xai.grok-4-fast-reasoning"
    api_key="OCI",
    base_url="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/v1",
    http_client=httpx.Client(
        auth=auth,
        headers={"CompartmentId": COMPARTMENT_ID}
    )
)
# llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
print(f"Using LLM: {llm.model_name}")


# --- 2. Tool Definitions (Simulated HR/IT Backend Service Calls) ---

# --- Worker A (HR Agent) Tools ---

def hr_check_pto_balance(employee_id: str) -> str:
    """
    Checks the current Paid Time Off (PTO) balance for a given employee ID by querying the HR backend system.
    This simulates a read-only query to a user record.
    """
    if employee_id.lower() == "jdoe123":
        return "PTO System Response: Success. Employee JDoe123 has 120 hours of Annual Leave and 32 hours of Sick Leave remaining."
    return f"PTO System Response: Error. Employee ID '{employee_id}' not found in the HR database."

def hr_retrieve_policy(policy_name: str) -> str:
    """
    Retrieves the summary text or a link to a specific HR policy document.
    This simulates accessing the document management system.
    """
    if "expense" in policy_name.lower():
        return "Policy Response: Expense Policy summary: All expenses over $50 must be pre-approved. Submit receipts within 30 days. Full policy: /policies/finance/expense_v2.pdf"
    elif "maternity" in policy_name.lower():
        return "Policy Response: Maternity Leave Policy summary: Provides 12 weeks of paid leave. Consult your HR partner for specifics. Full policy: /policies/hr/maternity_v1.pdf"
    return f"Policy Response: No policy found matching '{policy_name}'. Please specify the exact document name."

# --- Worker B (IT Agent) Tools ---

def it_reset_user_password(username: str) -> str:
    """
    Executes a password reset for a specified user account in the Active Directory (or similar IT system).
    This simulates a state-changing write operation.
    """
    if username.lower() in ["jsmith", "bjenkins"]:
        return f"IT System Response: Success. Password for user '{username}' has been securely reset. A temporary password has been sent to their alternate email."
    return f"IT System Response: Error. User '{username}' not found in Active Directory or is locked. Cannot reset."

def it_check_service_status(service_name: str) -> str:
    """
    Queries the IT monitoring dashboard to check the current operational status of a core system (e.g., Email, VPN).
    This simulates a diagnostic read query.
    """
    if "email" in service_name.lower():
        return "Monitoring Response: Email Service (Exchange) is currently operating at 99.8% uptime. Last downtime 4 days ago (15 minutes). Status: Operational."
    elif "vpn" in service_name.lower():
        return "Monitoring Response: VPN Gateway status is Degraded. High latency detected on nodes 3 and 5. Status: Investigating."
    return f"Monitoring Response: Service '{service_name}' status: Unknown or not monitored."


# Assign tools to workers
worker_a_tools = [hr_check_pto_balance, hr_retrieve_policy]
worker_b_tools = [it_reset_user_password, it_check_service_status]


# --- 3. Graph State Definition ---

# Define the state of the graph, which is passed between nodes
class AgentState(TypedDict):
    """Represents the state of our graph."""
    # The history of messages in the conversation
    messages: Annotated[List[BaseMessage], operator.add]
    # The next node to call (set by the supervisor)
    next: str


# --- 4. Worker Agent Setup (Tool-Enabled) ---

def create_worker_agent(llm, tools: list, system_prompt: str) -> AgentExecutor:
    """Helper function to create an OpenAI tool-calling agent."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )
    
    # Use create_tool_calling_agent (modern replacement)
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    # The AgentExecutor is what runs the agent with its tools
    executor = AgentExecutor(
        agent=agent, 
        tools=tools,
        # Allow the agent to run up to 5 tool-calling steps
        handle_parsing_errors=True,
        max_iterations=5, 
    )
    return executor

# Worker A: HR Agent
worker_a_system_prompt = (
    "You are Worker A, the dedicated Human Resources (HR) Service Agent. "
    "Your primary goal is to resolve service requests related to employee policies, benefits, and administration. "
    "Use your tools to check PTO balances or retrieve HR policies. "
    "Once you have a satisfactory answer, reply with a final, concise response to the user. "
    "You must only use the HR tools provided."
)
worker_a_executor = create_worker_agent(llm, worker_a_tools, worker_a_system_prompt)

# Worker B: IT Agent
worker_b_system_prompt = (
    "You are Worker B, the dedicated Information Technology (IT) Service Agent. "
    "Your primary goal is to resolve technical issues, check system health, and manage user accounts. "
    "Use your tools for password resets and checking the status of IT services. "
    "Once the action is complete or the status is confirmed, reply with a final, concise status report to the user. "
    "You must only use the IT tools provided."
)
worker_b_executor = create_worker_agent(llm, worker_b_tools, worker_b_system_prompt)


# Node function wrapper for Workers
def worker_node(state: AgentState, agent_executor: AgentExecutor, name: str) -> dict:
    """Runs a worker agent and updates the state."""
    print(f"--- Running {name} ---")
    
    # The input for the AgentExecutor is the list of messages in the state
    result = agent_executor.invoke({"messages": state["messages"]})
    
    # The result contains the new messages (output, tool calls, tool results)
    # We append the final output (typically the AIMessage) to the history
    output_message = result["output"]
    
    # LangGraph requires the output to be a dictionary matching the AgentState structure
    return {"messages": [output_message]}


# --- 5. Supervisor Agent Setup (Routing Logic) ---

# Schema for the supervisor's structured output
class Route(BaseModel):
    """The route to take next in the graph."""
    next: Annotated[str, Field(description="The name of the next node to route to.")]

# List of available worker names for the supervisor's instruction
WORKER_NAMES = ["Worker_A", "Worker_B", "FINISH"]

# Supervisor System Prompt
supervisor_prompt_text = (
    "You are the Supervisor Agent. Your role is to analyze the user's service request (SR) "
    "and determine which specialist agent should handle the task. "
    "You must output a JSON object indicating the 'next' node to transition to. "
    "Available worker nodes are: Worker_A (HR Agent: Policies, PTO, Admin) and Worker_B (IT Agent: Tech support, Accounts, System Status). "
    "If the request is complete, administrative, or requires no tool usage, select FINISH. "
    "Your decision must be based solely on the user's intent: "
    "1. Choose Worker_A for Human Resources questions (PTO, policies, benefits). "
    "2. Choose Worker_B for Information Technology issues (password reset, service status, technical support). "
    "3. Choose FINISH if the task is done or purely conversational. "
    "Always choose the single most appropriate worker."
)

# Supervisor agent (does not use tools)
supervisor_agent = (
    ChatPromptTemplate.from_messages([
        ("system", supervisor_prompt_text),
        MessagesPlaceholder(variable_name="messages"),
    ])
    | llm.with_structured_output(Route) # Force structured JSON output
)

# Node function wrapper for Supervisor
def route_supervisor(state: AgentState) -> dict:
    """Determines the next agent to call based on the supervisor's output."""
    print("--- Running Supervisor ---")
    
    # The input for the supervisor is the list of messages in the state
    result = supervisor_agent.invoke({"messages": state["messages"]})
    
    # The structured output is directly a dictionary with the 'next' key
    next_node = result.next
    
    # Validation
    if next_node not in WORKER_NAMES:
        print(f"WARNING: Supervisor chose invalid node '{next_node}'. Defaulting to FINISH.")
        next_node = "FINISH"
        
    print(f"--- Supervisor selected: {next_node} ---")
    
    # The output updates the 'next' key in the state
    return {"next": next_node}


# --- 6. Graph Construction and Compilation ---

# Create the graph instance
workflow = StateGraph(AgentState)

# Create partial functions for worker nodes to pass their specific executor and name
worker_a_node = partial(worker_node, agent_executor=worker_a_executor, name="Worker A (HR)")
worker_b_node = partial(worker_node, agent_executor=worker_b_executor, name="Worker B (IT)")

# Add nodes to the workflow
workflow.add_node("Supervisor", route_supervisor)
workflow.add_node("Worker_A", worker_a_node)
workflow.add_node("Worker_B", worker_b_node)

# Set the entry point
workflow.set_entry_point("Supervisor")

# Define edges (transitions)

# 1. From Supervisor to Workers/FINISH (Conditional Edges)
# The supervisor output determines the next step
workflow.add_conditional_edges(
    "Supervisor",
    lambda state: state["next"], # Use the 'next' field from the state to determine the path
    {
        "Worker_A": "Worker_A",
        "Worker_B": "Worker_B",
        "FINISH": END,
    },
)

# 2. From Workers to END (for a single task/SR resolution)
workflow.add_edge("Worker_A", END)
workflow.add_edge("Worker_B", END)


# Compile the graph
app = workflow.compile()

# --- 7. Example Usage ---

async def run_chat(prompt: str):
    """Runs a single conversation turn through the compiled graph."""
    
    # Initial state with the user's prompt
    initial_state = {"messages": [HumanMessage(content=prompt)]}
    print(f"\n[USER]: {prompt}")
    print("==================================================")
    
    # Stream the output
    async for step in app.astream(initial_state):
        # LangGraph stream output structure
        for key, value in step.items():
            if key in ["Supervisor"]:
                # The supervisor only updates the 'next' state, which is handled internally
                pass
            elif key in ["Worker_A", "Worker_B"]:
                # Print the worker's final response if it exists
                last_message = value.get("messages")[-1]
                if last_message and last_message.content:
                    print(f"[{key} Output]:\n{last_message.content}")
                    print("==================================================")
            elif key == '__end__':
                print(">>> Conversation ENDED <<<")


if __name__ == "__main__":
    import asyncio
    
    # Test 1: HR Query (Should route to Worker A) - PTO Check
    print("--- Test 1: HR SR (PTO Check for JDoe123) ---")
    asyncio.run(run_chat("What is my current PTO balance? My ID is JDoe123."))
    
    # Test 2: IT Query (Should route to Worker B) - Password Reset
    print("\n--- Test 2: IT SR (Password Reset for JSmith) ---")
    asyncio.run(run_chat("I forgot my password. Please reset the account for JSmith."))
    
    # Test 3: HR Query (Should route to Worker A) - Policy Retrieval
    print("\n--- Test 3: HR SR (Retrieve Policy) ---")
    asyncio.run(run_chat("Where can I find the details on the company expense policy?"))
    
    # Test 4: IT Query (Should route to Worker B) - Service Status
    print("\n--- Test 4: IT SR (Service Status Check) ---")
    asyncio.run(run_chat("Is the company email system working correctly right now?"))
    
    # Test 5: Conversational (Should route to FINISH)
    print("\n--- Test 5: Conversational (General Question) ---")
    asyncio.run(run_chat("Thank you for your help, I will check my email now."))