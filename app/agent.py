import re
import json
from pydantic import BaseModel, Field
from google.adk.workflow import Workflow, START, FunctionNode
from google.adk.agents.context import Context
from google.adk.events.request_input import RequestInput
import sys
from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool
from google.adk.tools import AgentTool, MCPToolset
from .config import config

from mcp import StdioServerParameters
mcp_toolset = MCPToolset(
    connection_params=StdioServerParameters(
        command=sys.executable,
        args=["app/mcp_server.py"]
    )
)

class HealthLinkState(BaseModel):
    user_issue: str = ""
    final_advice: str = ""

first_aid_specialist = LlmAgent(
    name="FirstAidSpecialist",
    description="Use this to get first aid advice for urgent but non-life-threatening situations.",
    model=config.model,
    instruction="""
    You provide immediate, basic first-aid guidance for non-life-threatening emergencies.
    Always advise the user to contact local emergency services if the situation is severe.
    You MUST call the `get_first_aid_steps` tool immediately using the user's condition to get instructions, and then present those steps directly. Do not ask the user clarifying questions.
    """,
    tools=[mcp_toolset]
)

telehealth_coordinator = LlmAgent(
    name="TeleHealthCoordinator",
    description="Use this to get tele-health referrals for medical conditions requiring a doctor.",
    model=config.model,
    instruction="""
    You help coordinate tele-health resources for users needing a doctor.
    You identify the appropriate specialist or general practitioner needed based on their symptoms.
    You MUST call the `find_nearby_clinics` or `check_symptom_severity` tools immediately to get clinic info or severity details, and present them directly. Do not ask clarifying questions.
    """,
    tools=[mcp_toolset]
)

first_aid_tool = AgentTool(agent=first_aid_specialist)
telehealth_tool = AgentTool(agent=telehealth_coordinator)

orchestrator = LlmAgent(
    name="TriageOrchestrator",
    model=config.model,
    instruction="""
    You are the initial contact for the HealthLink system.
    Evaluate the user's issue and determine the best course of action.
    Use the FirstAidSpecialist tool if the user needs immediate first aid.
    Use the TeleHealthCoordinator tool if the user needs a doctor referral or diagnosis.
    Once a sub-agent returns the information, you MUST compile it and return a detailed final summary of the advice to the user. Do not return empty response.
    """,
    tools=[first_aid_tool, telehealth_tool]
)

def intake(ctx: Context, node_input: str):
    ctx.state["user_issue"] = node_input

def security_checkpoint(ctx: Context):
    user_input = ctx.state["user_issue"]
    
    # Prompt Injection Detection
    injection_keywords = ["ignore previous", "system prompt", "bypass", "override"]
    if any(kw in user_input.lower() for kw in injection_keywords):
        ctx.state["final_advice"] = "SECURITY EVENT: Prompt injection detected."
        print(json.dumps({"event": "injection_detected", "severity": "CRITICAL"}))
        ctx.route = "output_result"
        return
        
    # Domain-Specific Rule: Critical Keyword Escelation
    if "suicide" in user_input.lower():
        ctx.state["final_advice"] = "SECURITY EVENT: Please contact an emergency hotline immediately."
        print(json.dumps({"event": "critical_keyword", "severity": "CRITICAL"}))
        ctx.route = "output_result"
        return
        
    # PII Scrubbing
    scrubbed_input = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[REDACTED PHONE]', user_input)
    scrubbed_input = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED SSN]', scrubbed_input)
    
    if scrubbed_input != user_input:
        print(json.dumps({"event": "pii_scrubbed", "severity": "WARNING"}))
    
    ctx.state["user_issue"] = scrubbed_input
    print(json.dumps({"event": "security_check_passed", "severity": "INFO"}))
    
    ctx.route = "triage"

async def triage_impl(ctx: Context):
    response = await ctx.run_node(orchestrator)
    ctx.state["final_advice"] = response.text if hasattr(response, 'text') else str(response)

triage = FunctionNode(func=triage_impl, rerun_on_resume=True, name="triage")

def human_approval(ctx: Context) -> RequestInput:
    return RequestInput(
        prompt=f"Please review the following advice before providing to user: {ctx.state['final_advice']}\n\nType 'approve' to send or 'deny' to stop."
    )

def after_approval(ctx: Context, node_input: str):
    user_input = node_input.lower()
    if "approve" not in user_input:
        ctx.state["final_advice"] = "Advice was denied by human reviewer."

def output_result(ctx: Context) -> str:
    return ctx.state["final_advice"]

app = Workflow(
    name="healthlink",
    state_schema=HealthLinkState,
    edges=[
        (START, intake, security_checkpoint),
        (security_checkpoint, {"triage": triage, "output_result": output_result}),
        (triage, human_approval, after_approval, output_result),
    ]
)

object.__setattr__(app, 'root_agent', app)
root_agent = app
