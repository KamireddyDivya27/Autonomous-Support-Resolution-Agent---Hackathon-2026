# Failure Mode Analysis

## Failure Mode 1: Tool Timeout / Network Error
**Scenario:** `get_order` or `check_refund_eligibility` times out or returns a network error.

**How the system responds:**
- The `_execute_tool` method wraps every tool call in a try/except block
- The failure is caught, logged with full error message and duration
- `state["error_occurred"]` is set to True
- The tool call is recorded in `tool_calls` with `success: False`
- In `_decide`, if successful tool count falls below threshold, ticket is escalated
- The ticket is NEVER dropped — it always reaches a terminal state (RESOLVED or ESCALATED)

**Evidence in code:** `src/agents/support_agent.py` `_execute` method, lines with `except Exception as e`

---

## Failure Mode 2: LLM Returns Malformed JSON (Classification Failure)
**Scenario:** The LLM returns markdown-wrapped JSON, partial JSON, or plain text instead of a valid JSON object.

**How the system responds:**
- Raw response is logged immediately for debugging
- Regex strips markdown code fences (` ``` `)
- Regex extracts the first `{...}` JSON object found in the response
- If JSON still fails to parse, classification defaults to `UNKNOWN` with confidence 0.3
- Low confidence triggers `requires_escalation = True` in the PLAN step
- Ticket is escalated with reasoning: "Parse error: ..."

**Evidence in code:** `src/agents/support_agent.py` `_classify` method with multi-stage JSON extraction

---

## Failure Mode 3: Refund Issued Without Eligibility Check (Safety Gate)
**Scenario:** Agent attempts to call `issue_refund` on an order that is outside the 30-day return window or already refunded.

**How the system responds:**
- `validate_preconditions` checks two conditions before allowing `issue_refund`:
  1. `eligibility_checked` — `check_refund_eligibility` must have run successfully
  2. `is_eligible` — the result must explicitly confirm eligibility
- If either condition fails, a `ValueError` is raised and the tool call is blocked
- The failure is logged as an expected safety gate trigger (not a system error)
- The agent continues to `send_reply` with an appropriate message to the customer
- The refund is never issued for ineligible orders

**Evidence in run:** TKT-003 (45-day-old keyboard) — `issue_refund` blocked, ticket still RESOLVED with customer reply

---

## Failure Mode 4: Concurrent Rate Limiting
**Scenario:** Multiple tickets processed simultaneously hit OpenRouter free tier rate limits (429 errors).

**How the system responds:**
- Each ticket runs in its own asyncio task
- HTTP errors from OpenRouter are caught at the LangChain layer
- Classification failure fallback (Failure Mode 2) activates
- Failed tickets are escalated rather than crashing the entire batch
- The processing summary still reports accurate counts

---

## Failure Mode 5: Missing Order ID in Ticket Message
**Scenario:** Customer writes about a refund but does not include an order ID in their message.

**How the system responds:**
- `_intake` uses regex to extract order IDs matching pattern `ORD-\d+`
- If no match found, `mentioned_order_id` is not set in `tool_results`
- When `get_order` is called and finds no order ID, it raises `ValueError: No order ID found`
- This tool failure is caught and logged
- `_decide` sees insufficient successful tools and escalates
- Human agent receives full context including what information was missing
