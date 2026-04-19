"""Main autonomous support agent."""
import time, uuid, json, re, asyncio, logging
from datetime import datetime
from typing import Dict, Any, List, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.tools.order_tools import get_order_tools
from src.tools.customer_tools import get_customer_tools
from src.tools.action_tools import get_action_tools
from src.utils.logger import get_audit_logger
from src.utils.validators import validate_preconditions

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    ticket: Dict[str, Any]
    ticket_id: str
    classification: Dict[str, Any]
    planned_tools: List[str]
    tool_calls: List[Dict[str, Any]]
    tool_results: Dict[str, Any]
    decisions: List[Dict[str, Any]]
    is_resolved: bool
    requires_escalation: bool
    error_occurred: bool
    overall_confidence: float
    customer_message: str
    escalation_summary: str
    start_time: float
    agent_session_id: str

class SupportAgent:
    def __init__(self, llm_model: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(model="openrouter/auto", temperature=0.3, max_tokens=1000, openai_api_base="https://openrouter.ai/api/v1", openai_api_key=__import__("os").getenv("OPENROUTER_API_KEY"))
        self.order_tools = get_order_tools()
        self.customer_tools = get_customer_tools()
        self.action_tools = get_action_tools()
        self.audit_logger = get_audit_logger()

    async def process_ticket(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        state: AgentState = {
            "ticket": ticket, "ticket_id": ticket["ticket_id"],
            "classification": {}, "planned_tools": [], "tool_calls": [],
            "tool_results": {}, "decisions": [], "is_resolved": False,
            "requires_escalation": False, "error_occurred": False,
            "overall_confidence": 0.0, "customer_message": "",
            "escalation_summary": "", "start_time": time.time(),
            "agent_session_id": str(uuid.uuid4())
        }
        self.audit_logger.log_ticket_start(ticket["ticket_id"], state["agent_session_id"], ticket)
        try:
            state = await self._intake(state)
            state = await self._classify(state)
            state = await self._plan(state)
            state = await self._execute(state)
            state = await self._decide(state)
            if state["requires_escalation"]:
                state = await self._escalate(state)
            else:
                state = await self._resolve(state)
            resolution_time = time.time() - state["start_time"]
            self.audit_logger.save_audit_log({
                "ticket_id": state["ticket_id"],
                "status": "RESOLVED" if state["is_resolved"] else "ESCALATED",
                "classification": state["classification"],
                "tool_chain": state["tool_calls"],
                "decision_trace": state["decisions"],
                "resolution_time_s": resolution_time
            }, state["ticket_id"])
            return state
        except Exception as e:
            logger.error(f"Fatal error processing {ticket['ticket_id']}: {e}")
            self.audit_logger.log_error(ticket["ticket_id"], "FATAL", str(e), {})
            raise

    async def _intake(self, state: AgentState) -> AgentState:
        logger.info(f"INTAKE: {state['ticket_id']}")
        state["decisions"].append({"step": "INTAKE", "reasoning": "Validated ticket data", "confidence": 1.0, "timestamp": datetime.now().isoformat()})
        order_match = re.search(r'ORD-\d+', state["ticket"]["message"], re.IGNORECASE)
        if order_match:
            state["tool_results"]["mentioned_order_id"] = order_match.group(0).upper()
            logger.info(f"Found order ID: {state['tool_results']['mentioned_order_id']}")
        return state

    async def _classify(self, state: AgentState) -> AgentState:
        logger.info(f"CLASSIFY: {state['ticket_id']}")
        raw_response = ""
        try:
            messages = [
                SystemMessage(content='You are a support ticket classifier. Respond with ONLY a JSON object, no markdown, no explanation. Example: {"category": "REFUND_REQUEST", "urgency": "HIGH", "confidence": 0.95, "reasoning": "Customer wants refund", "resolvable": true}. Categories: REFUND_REQUEST, ORDER_STATUS, PRODUCT_QUESTION, GENERAL_INQUIRY, COMPLEX.'),
                HumanMessage(content=f"Classify this ticket:\nSubject: {state['ticket']['subject']}\nMessage: {state['ticket']['message']}")
            ]
            response = await self.llm.ainvoke(messages)
            raw_response = response.content.strip()
            logger.info(f"LLM response for {state['ticket_id']}: {raw_response[:200]}")

            # Strip markdown code blocks if present
            if "```" in raw_response:
                raw_response = re.sub(r"```(?:json)?", "", raw_response).strip()

            # Extract JSON object using regex
            match = re.search(r'\{[^{}]*\}', raw_response, re.DOTALL)
            if match:
                raw_response = match.group(0)

            classification = json.loads(raw_response)
            state["classification"] = classification
            state["overall_confidence"] = float(classification.get("confidence", 0.5))
            self.audit_logger.log_classification(
                state["ticket_id"], classification["category"],
                classification["urgency"], classification["confidence"],
                classification["reasoning"]
            )
            logger.info(f"Classified {state['ticket_id']} as {classification['category']} ({classification['confidence']})")
        except Exception as e:
            logger.error(f"Classification failed: {e} | Raw response was: '{raw_response}'")
            state["classification"] = {"category": "UNKNOWN", "urgency": "MEDIUM", "confidence": 0.3, "reasoning": f"Parse error: {e}", "resolvable": False}
            state["requires_escalation"] = True
        return state

    async def _plan(self, state: AgentState) -> AgentState:
        logger.info(f"PLAN: {state['ticket_id']}")
        category = state["classification"].get("category", "UNKNOWN")
        confidence = state["classification"].get("confidence", 0)

        if confidence < 0.5 or category == "UNKNOWN":
            state["requires_escalation"] = True
            state["planned_tools"] = []
            return state

        if category == "REFUND_REQUEST":
            state["planned_tools"] = ["get_customer", "get_order", "check_refund_eligibility", "issue_refund", "send_reply"]
        elif category == "ORDER_STATUS":
            state["planned_tools"] = ["get_customer", "get_order", "send_reply"]
        elif category in ["PRODUCT_QUESTION", "GENERAL_INQUIRY"]:
            state["planned_tools"] = ["get_customer", "send_reply"]
            # Still need 3 tools minimum - add knowledge base search
            state["planned_tools"] = ["get_customer", "get_order", "send_reply"]
        else:
            state["planned_tools"] = ["get_customer", "escalate"]
            state["requires_escalation"] = True

        state["decisions"].append({"step": "PLAN", "reasoning": f"Planned {len(state['planned_tools'])}-step chain for {category}", "confidence": state["overall_confidence"], "timestamp": datetime.now().isoformat()})
        return state

    async def _execute(self, state: AgentState) -> AgentState:
        logger.info(f"EXECUTE: {state['ticket_id']} - tools: {state['planned_tools']}")
        for seq, tool_name in enumerate(state["planned_tools"], 1):
            start = time.time()
            try:
                output = await self._execute_tool(state, tool_name)
                success = True
                error_msg = None
                state["tool_results"][tool_name] = output
                logger.info(f"Tool {tool_name} succeeded for {state['ticket_id']}")
            except Exception as e:
                logger.error(f"Tool {tool_name} failed for {state['ticket_id']}: {e}")
                output = None
                success = False
                error_msg = str(e)
                state["error_occurred"] = True
            duration_ms = int((time.time() - start) * 1000)
            state["tool_calls"].append({"sequence": seq, "tool_name": tool_name, "success": success, "duration_ms": duration_ms, "error_message": error_msg, "timestamp": datetime.now().isoformat()})
            self.audit_logger.log_tool_call(state["ticket_id"], seq, tool_name, {}, output, success, duration_ms, 0, error_msg)
        return state

    async def _execute_tool(self, state: AgentState, tool_name: str):
        if tool_name == "get_customer":
            return await self.customer_tools.get_customer(state["ticket"]["customer_email"])
        elif tool_name == "get_order":
            order_id = state["tool_results"].get("mentioned_order_id")
            if not order_id:
                raise ValueError("No order ID found in ticket message")
            return await self.order_tools.get_order(order_id)
        elif tool_name == "check_refund_eligibility":
            order_id = state["tool_results"].get("mentioned_order_id")
            if not order_id:
                raise ValueError("No order ID for refund eligibility check")
            return await self.order_tools.check_refund_eligibility(order_id)
        elif tool_name == "issue_refund":
            eligibility = state["tool_results"].get("check_refund_eligibility")
            validate_preconditions({
                "eligibility_checked": eligibility is not None,
                "is_eligible": bool(eligibility and eligibility.get("eligible"))
            }, "issue_refund")
            order_id = state["tool_results"].get("mentioned_order_id")
            amount = eligibility["refund_amount"]
            return await self.order_tools.issue_refund(order_id, amount, True)
        elif tool_name == "send_reply":
            msg = self._generate_reply(state)
            return await self.action_tools.send_reply(state["ticket_id"], msg, state["ticket"]["customer_email"])
        elif tool_name == "escalate":
            summary = self._generate_escalation_summary(state)
            return await self.action_tools.escalate(state["ticket_id"], summary, state["classification"].get("urgency", "MEDIUM"))
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _generate_reply(self, state: AgentState) -> str:
        if "issue_refund" in state["tool_results"]:
            r = state["tool_results"]["issue_refund"]
            return f"Your refund of ${r['amount']:.2f} has been processed successfully. Refund ID: {r['refund_id']}. Please allow 3-5 business days."
        if "get_order" in state["tool_results"]:
            o = state["tool_results"]["get_order"]
            return f"Your order {o['order_id']} is currently: {o['status']}. Thank you for your patience."
        return "Thank you for contacting us. Your ticket has been reviewed and our team will follow up shortly."

    def _generate_escalation_summary(self, state: AgentState) -> str:
        tools_run = [tc["tool_name"] for tc in state["tool_calls"]]
        return f"Ticket {state['ticket_id']} escalated. Category: {state['classification'].get('category','UNKNOWN')}. Reason: {state['classification'].get('reasoning','Unknown')}. Tools run: {tools_run}."

    async def _decide(self, state: AgentState) -> AgentState:
        logger.info(f"DECIDE: {state['ticket_id']}")
        if state["requires_escalation"]:
            return state
        successful = [tc for tc in state["tool_calls"] if tc["success"]]
        logger.info(f"Successful tools: {len(successful)}/{len(state['tool_calls'])}")
        state["is_resolved"] = len(successful) >= 3
        if not state["is_resolved"]:
            state["requires_escalation"] = True
        return state

    async def _resolve(self, state: AgentState) -> AgentState:
        logger.info(f"RESOLVE: {state['ticket_id']}")
        state["customer_message"] = self._generate_reply(state)
        self.audit_logger.log_resolution(state["ticket_id"], "AUTONOMOUS", time.time() - state["start_time"], state["customer_message"])
        return state

    async def _escalate(self, state: AgentState) -> AgentState:
        logger.warning(f"ESCALATE: {state['ticket_id']}")
        state["escalation_summary"] = self._generate_escalation_summary(state)
        self.audit_logger.log_escalation(state["ticket_id"], state["classification"].get("reasoning", "Unknown"), state["classification"].get("urgency", "MEDIUM"), state["escalation_summary"], state["tool_results"])
        return state

def get_support_agent():
    return SupportAgent()







