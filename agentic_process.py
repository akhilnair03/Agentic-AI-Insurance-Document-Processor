# Virtual Medical Biller: Enhanced Agentic Version

# Imports
import json
import time
import os
import logging
from typing import TypedDict, Annotated, Sequence, Literal, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent, ToolNode
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from utils import (
    CMS1500Filler,
    compare_forms,
    extract_diagnostic_report_text
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Utility Functions

def safe_json_dumps(obj):
    """
    Safely dumps objects to JSON, handling custom classes like HumanMessage.
    """
    def default(o):
        if isinstance(o, BaseMessage):
            return {"type": o.__class__.__name__, "content": o.content}
        return str(o)
    return json.dumps(obj, indent=2, default=default)

# LLM Initialization

llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

# Agent State Definition

class AgentState(TypedDict):
    """
    Agent state structure used in the workflow.
    """
    messages: Annotated[Sequence[BaseMessage], "Messages in the conversation"]
    fhir_bundle: Annotated[dict, "FHIR bundle being processed"]
    raw_data: Annotated[Optional[dict], "Extracted raw data"]
    ground_truth: Annotated[Optional[dict], "Ground truth data"]
    current_step: Annotated[Literal["extract_raw", "extract_gt", "fill_raw", "fill_gt", "compare", "done"], "Current processing step"]
    error: Annotated[Optional[str], "Error message if any"]

# Tool Definitions

@tool
def extract_from_raw(state: dict) -> dict:
    """
    Extract CMS-1500 fields from raw clinical note.
    """
    logger.info("Tool: extract_from_raw called")
    logger.info(f"State at extract_from_raw:\n{safe_json_dumps(state)}")
    try:
        start_time = time.time()
        raw_text = extract_diagnostic_report_text(state["fhir_bundle"])

        prompt = f"""
You are a medical billing assistant. Extract the following CMS-1500 fields:
...
Clinical Note:
{raw_text}
"""
        output = llm.invoke(prompt)
        json_str = output.content if hasattr(output, 'content') else output
        logger.info(f"Successfully extracted raw data in {time.time() - start_time:.2f} seconds")
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"Error in extract_from_raw: {str(e)}")
        raise

@tool
def extract_ground_truth(state: dict) -> dict:
    """
    Extract CMS-1500 fields from structured FHIR data.
    """
    logger.info("Tool: extract_ground_truth called")
    logger.info(f"State at extract_ground_truth:\n{safe_json_dumps(state)}")
    try:
        start_time = time.time()
        patient = next(r['resource'] for r in state["fhir_bundle"]['entry'] if r['resource']['resourceType'] == 'Patient')
        claim = next(r['resource'] for r in state["fhir_bundle"]['entry'] if r['resource']['resourceType'] == 'Claim')
        encounter = next(r['resource'] for r in state["fhir_bundle"]['entry'] if r['resource']['resourceType'] == 'Encounter')
        organization = next((r['resource'] for r in state["fhir_bundle"]['entry'] if r['resource']['resourceType'] == 'Organization'), {})

        phone = next((tele['value'] for tele in patient.get('telecom', []) if tele['system'] == 'phone'), '')
        insurance_id = claim.get('insurance', [{}])[0].get('coverage', {}).get('reference', '').split('/')[-1]
        other_insurance_name = claim.get('insurance', [{}])[1]['coverage']['display'] if len(claim.get('insurance', [])) > 1 else ''
        accident_related = 'Yes' if 'accident' in claim else 'No'
        prior_auth_number = claim.get('preAuthRef', [''])[0] if claim.get('preAuthRef') else ''

        billing_provider_name = organization.get('name', '')
        billing_address_parts = organization.get('address', [{}])[0]
        billing_provider_address = f"{billing_address_parts.get('line', [''])[0]} {billing_address_parts.get('city', '')}, {billing_address_parts.get('state', '')} {billing_address_parts.get('postalCode', '')}"

        logger.info(f"Successfully extracted ground truth in {time.time() - start_time:.2f} seconds")
        return {
            'patient_name': f"{patient['name'][0]['given'][0]} {patient['name'][0]['family']}",
            'dob': patient['birthDate'],
            'gender': patient['gender'],
            'address': f"{patient['address'][0]['line'][0]}, {patient['address'][0]['city']}, {patient['address'][0]['state']} {patient['address'][0]['postalCode']}",
            'phone_number': phone,
            'relationship_to_insured': 'self',
            'insurance_name': claim['insurance'][0]['coverage']['display'],
            'insurance_id': insurance_id,
            'other_insurance_name': other_insurance_name,
            'accident_related': accident_related,
            'prior_auth_number': prior_auth_number,
            'provider_name': encounter['participant'][0]['individual']['display'],
            'provider_npi': encounter['participant'][0]['individual']['reference'].split('|')[-1],
            'service_facility_name': encounter['location'][0]['location']['display'],
            'billing_provider_name': billing_provider_name,
            'billing_provider_address': billing_provider_address,
            'diagnosis_codes': [item['productOrService']['coding'][0]['code'] for item in claim['item']],
            'procedure_codes': [item['productOrService']['coding'][0]['code'] for item in claim['item']],
            'date_of_service': encounter['period']['start'].split('T')[0],
            'total_charge': claim['total']['value'],
            'physician_signature': 'Signature on File'
        }
    except Exception as e:
        logger.error(f"Error in extract_ground_truth: {str(e)}")
        raise

@tool
def fill_form(state: dict, filename: str) -> str:
    """
    Fill CMS-1500 PDF form with the provided data.
    """
    logger.info(f"Tool: fill_form called with filename={filename}")
    logger.info(f"State at fill_form:\n{safe_json_dumps(state)}")
    try:
        data = state["raw_data"] if "raw" in filename else state["ground_truth"]
        result = CMS1500Filler().fill(data, filename)
        logger.info(f"Form filled successfully: {filename}")
        return result
    except Exception as e:
        logger.error(f"Error in fill_form: {str(e)}")
        raise

@tool
def compare_forms_wrapper(state: dict) -> str:
    """
    Compare two filled CMS-1500 forms and generate a comparison report.
    """
    logger.info(f"Tool: compare_forms_wrapper called")
    logger.info(f"State at compare_forms_wrapper:\n{safe_json_dumps(state)}")
    try:
        result = compare_forms(state["raw_data"], state["ground_truth"])
        logger.info(f"Forms compared successfully")
        return result
    except Exception as e:
        logger.error(f"Error in compare_forms_wrapper: {str(e)}")
        raise

# Fixed Custom ToolNode

class StatefulToolNode(ToolNode):
    """
    Modified ToolNode that properly injects full agent state into tools.
    """
    def __init__(self, tools):
        super().__init__(tools)

    def invoke(self, state: AgentState, config=None):
        logger.info(f"Invoking tool node with state current_step={state['current_step']}")
        messages = state["messages"]
        last_message = messages[-1]
        
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            tool_call = last_message.tool_calls[0]
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args", {}) or {}

            logger.info(f"⚡ Tool requested by agent: {tool_name}, args={tool_args}")

            tool = next((t for t in self.tools if t.name == tool_name), None)
            if tool is None:
                raise ValueError(f"Tool {tool_name} not found.")

            # Correctly inject 'state'
            if "state" in tool.args:
                tool_args["state"] = state

            return tool.invoke(tool_args)
        else:
            logger.warning("No tool call detected.")
            return {}

# Process Agent Response

def process_agent_response(state: AgentState, response: AIMessage) -> AgentState:
    """
    Update agent state based on the agent's response.
    """
    content = response.content.lower()
    logger.info(f"Agent response content: {content}")
    state_transitions = {
        "extract_raw": "extract_gt",
        "extract_gt": "fill_raw",
        "fill_raw": "fill_gt",
        "fill_gt": "compare",
        "compare": "done"
    }
    if "next_step" in content:
        current_step = state["current_step"]
        if current_step in state_transitions:
            logger.info(f"Moving from {current_step} to {state_transitions[current_step]}")
            state["current_step"] = state_transitions[current_step]
    elif "done" in content:
        logger.info(f"Processing DONE.")
        state["current_step"] = "done"
    return state

# Main Execution

def main():
    """
    Main function to initialize and run the agentic Virtual Medical Biller.
    """
    start_time = time.time()
    logger.info("Starting main process...")

    try:
        with open("synthea/output/fhir/Geoffrey157_O'Conner199_de240e7a-b512-b2a5-c27a-89229fb23655.json") as f:
            fhir_bundle = json.load(f)

        tools = [
            extract_from_raw,
            extract_ground_truth,
            fill_form,
            compare_forms_wrapper
        ]

        tool_node = StatefulToolNode(tools)

        agent_runnable = create_react_agent(
            model=llm,
            tools=tools,
            prompt="""You are a medical billing assistant. Follow steps: 
1. Extract raw 
2. Extract structured 
3. Fill forms 
4. Compare 
After each step say NEXT_STEP."""
        )

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", agent_runnable)
        workflow.add_node("tools", tool_node)
        workflow.add_edge("agent", "tools")
        workflow.add_edge("tools", "agent")
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)

        app = workflow.compile()

        initial_state = {
            "messages": [HumanMessage(content="Begin processing the FHIR bundle.")],
            "fhir_bundle": fhir_bundle,
            "raw_data": None,
            "ground_truth": None,
            "current_step": "extract_raw",
            "error": None
        }

        logger.info("Starting agent execution...")
        for output in app.stream(initial_state):
            if output:
                for key, value in output.items():
                    logger.info(f"Output from node '{key}':")
                    logger.info(value)
                    if key == "agent" and isinstance(value, AIMessage):
                        initial_state = process_agent_response(initial_state, value)
            else:
                logger.info("Waiting for output...")
            time.sleep(8)

        logger.info(f"Total execution time: {time.time() - start_time:.2f} seconds")

    except Exception as e:
        logger.error(f"Fatal error in main process: {str(e)}")
        raise

if __name__ == "__main__":
    main()
