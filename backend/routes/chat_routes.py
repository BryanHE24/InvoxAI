# backend/routes/chat_routes.py
from flask import Blueprint, request, jsonify, current_app
import logging
import json
from datetime import datetime, timedelta
import re 

logger = logging.getLogger(__name__)
chat_bp = Blueprint('chat_bp', __name__)

def get_structured_intent_from_query(openai_service, user_query):
    if not openai_service:
        logger.error("OpenAI service not available for NLU preprocessing in chat_routes.")
        return {"intent": "error_no_openai_service", "entities": {}, "error": "OpenAI service unavailable."}
    current_date_str = datetime.now().strftime('%Y-%m-%d')
    nlu_system_prompt = f"""
You are an expert Natural Language Understanding (NLU) system for an invoice management chatbot named InvoxAI.
Your task is to analyze the user's query and convert it into a structured JSON object.
The JSON object should identify the user's primary 'intent' and any relevant 'entities'.
Output ONLY the JSON object. Do not add any explanatory text, greetings, or markdown backticks. Just the raw JSON.
Supported Intents:
- "get_total_spend": User wants a sum of money (e.g., total spent, spend on X).
- "list_invoices": User wants a list of invoices (default if specific criteria given).
- "count_invoices": User wants a number of invoices.
- "get_invoice_detail": User is asking about a specific invoice by ID (e.g., "details for invoice 123").
- "general_query": If the intent is unclear, a general question, or a greeting.
Entities to Extract (if present, otherwise omit or set to null):
- "vendor_name": (string) The name of the vendor.
- "category": (string) The expense category.
- "status": (string, e.g., "processed", "pending_textract", "error")
- "invoice_id": (integer) A specific invoice ID.
- "date_exact": (string "YYYY-MM-DD") A specific single date.
- "date_range": (object {{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}}) A period.
  - For "last month", "this month", "next month", "last week", "this week", "next week", "last year", "this year", "next year", "yesterday", "today", "tomorrow".
  - For month names like "April" or "April 2023".
- "month_year": (string "YYYY-MM") A specific month and year.
- "year": (string "YYYY") A specific year.
- "amount_filter": (object {{"operator": ">"|"<"|">="|"<="|"=", "value": float}}) e.g., "invoices over $100".
- "sort_by": (string, e.g., "date_desc", "amount_asc", "vendor_name_asc") If user implies an order.
- "limit_results": (integer) If user asks for "top 5", "first 3", etc. (Default to 5 if listing).
Current date for relative calculations: {current_date_str}
Example User Query: "Show me processed invoices from Dell for last April over $50, sort by amount descending."
Expected JSON Output Example (only this, no other text):
{{  "intent": "list_invoices",  "entities": {{    "status": "processed",    "vendor_name": "Dell",    "month_year": "{ (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1, month=4).strftime('%Y-%m') if datetime.now().month > 4 else (datetime.now().replace(day=1, year=datetime.now().year-1) - timedelta(days=1)).replace(day=1, month=4).strftime('%Y-%m') }",    "amount_filter": {{"operator": ">", "value": 50.0}},    "sort_by": "amount_desc",    "limit_results": 5  }}}}"""
    messages = [{"role": "system", "content": nlu_system_prompt.strip()}, {"role": "user", "content": user_query}]
    try:
        logger.info("NLU: Calling OpenAI for intent/entity extraction.")
        raw_nlu_response = openai_service.get_chat_completion(messages, model="gpt-3.5-turbo", temperature=0.1, max_tokens=600)
        if raw_nlu_response and raw_nlu_response.startswith("ERROR_OPENAI_"): logger.error(f"NLU call to OpenAI failed: {raw_nlu_response}"); return {"intent": "error_nlu_call_failed", "entities": {}, "error": raw_nlu_response}
        logger.debug(f"NLU: Raw response from OpenAI: {raw_nlu_response}")
        cleaned_response = raw_nlu_response.strip();
        if cleaned_response.startswith("```json"): cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"): cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"): cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
        nlu_result = json.loads(cleaned_response)
        logger.info(f"NLU: Structured result: {json.dumps(nlu_result, indent=2)}")
        # Ensure 'entities' key exists and is a dict, even if NLU returns null for it
        if 'entities' not in nlu_result or not isinstance(nlu_result['entities'], dict):
            logger.warning(f"NLU result had missing or non-dict 'entities'. Defaulting to empty dict. Original entities: {nlu_result.get('entities')}")
            nlu_result['entities'] = {}
        return nlu_result
    except json.JSONDecodeError as e:
        logger.error(f"NLU: Failed to decode JSON from NLU response: {e}. Raw response: '{raw_nlu_response}'")
        return {"intent": "general_query", "entities": {}, "error": "NLU_json_decode_error", "details": str(e), "original_nlu_response": raw_nlu_response}
    except Exception as e:
        logger.error(f"NLU: Error during NLU preprocessing call: {e}", exc_info=True)
        return {"intent": "general_query", "entities": {}, "error": "NLU_exception", "details": str(e)}

def build_context_from_structured_intent(db_service, structured_nlu):
    if not db_service:
        logger.warning("DbService not available for structured context building.")
        return "Database service is not available to fetch context."
    if not structured_nlu or "intent" not in structured_nlu or structured_nlu.get("error"):
        logger.warning(f"No valid structured NLU data for context. NLU result: {structured_nlu}")
        return "I had trouble understanding the specifics of your request for invoice data."

    intent = structured_nlu.get("intent")
    # *** ENSURE entities IS A DICTIONARY HERE ***
    entities = structured_nlu.get("entities") 
    if not isinstance(entities, dict): # If entities is None or not a dict
        logger.info(f"NLU returned non-dict entities ('{entities}'), defaulting to empty dict for context builder.")
        entities = {} # Default to empty dictionary
    
    logger.info(f"Context Builder: Intent='{intent}', Entities='{json.dumps(entities, indent=2)}'")

    db_filters = {}
    # Now it's safe to use entities.get()
    limit = entities.get("limit_results") if isinstance(entities.get("limit_results"), int) and entities.get("limit_results") > 0 else 5 

    if entities.get("vendor_name"): db_filters["vendor_name_like"] = entities.get("vendor_name")
    if entities.get("category"): db_filters["user_category_like"] = entities.get("category")
    if entities.get("status"): db_filters["status_exact_match"] = entities.get("status")
    if entities.get("invoice_id") and isinstance(entities.get("invoice_id"), int):
        db_filters["id_exact_match"] = entities.get("invoice_id")

    if entities.get("date_exact"): db_filters["invoice_date_exact"] = entities.get("date_exact")
    if entities.get("date_range"):
        db_filters["invoice_date_start"] = entities.get("date_range", {}).get("start_date")
        db_filters["invoice_date_end"] = entities.get("date_range", {}).get("end_date")
    if entities.get("month_year"):
        try:
            year, month = map(int, entities.get("month_year").split('-'))
            start_date = datetime(year, month, 1); end_month = month + 1 if month < 12 else 1
            end_year = year if month < 12 else year + 1
            end_date = datetime(end_year, end_month, 1) - timedelta(days=1)
            db_filters["invoice_date_start"] = start_date.strftime('%Y-%m-%d')
            db_filters["invoice_date_end"] = end_date.strftime('%Y-%m-%d')
        except Exception as e: logger.warning(f"Could not parse month_year: {e}")
    elif entities.get("year"): # Check this only if month_year wasn't provided
        year_str = str(entities.get("year", "")) # Default to empty string if year is None
        if len(year_str) == 4 and year_str.isdigit():
             db_filters["invoice_date_start"] = f"{year_str}-01-01"; db_filters["invoice_date_end"] = f"{year_str}-12-31"

    if entities.get("amount_filter"):
        op = entities.get("amount_filter", {}).get("operator"); val = entities.get("amount_filter", {}).get("value")
        if op and val is not None:
            try: 
                float_val = float(val)
                if op == ">": db_filters["total_amount_gt"] = float_val
                elif op == "<": db_filters["total_amount_lt"] = float_val
            except ValueError: logger.warning(f"Invalid amount value for filter: {val}")
    
    sort_map = {"date_desc": "invoice_date DESC", "amount_asc": "total_amount ASC", "id_desc": "id DESC"}
    db_filters["order_by"] = sort_map.get(entities.get("sort_by"), "invoice_date DESC, id DESC")

    relevant_invoices = []
    # Only query DB if intent suggests we need invoice list/details or data for calculation
    if intent in ["list_invoices", "count_invoices", "get_total_spend", "get_invoice_detail", "general_query"]: # Added general_query to fetch some context
        try:
            logger.info(f"Context Builder: Querying DB with filters: {db_filters}, limit: {limit}")
            # Ensure db_service.get_invoices_by_filter is robust and exists
            if hasattr(db_service, 'get_invoices_by_filter'):
                 relevant_invoices = db_service.get_invoices_by_filter(db_filters, limit=limit)
            else:
                 logger.error("DbService missing get_invoices_by_filter method! Falling back.")
                 relevant_invoices = db_service.get_all_invoices(limit=limit) # Fallback
            logger.info(f"Context Builder: Found {len(relevant_invoices)} invoices matching criteria.")
        except Exception as e:
            logger.error(f"Context Builder: Error querying DB: {e}", exc_info=True)
            return "Error retrieving data from the database for context."
    
    if intent == "count_invoices": return f"I found {len(relevant_invoices)} invoice(s) matching your criteria."
    if intent == "get_total_spend":
        if not relevant_invoices: return "I couldn't find any invoices matching your criteria to calculate total spend."
        total_spend = sum(inv.get('total_amount', 0) or 0 for inv in relevant_invoices)
        currency_found = next((inv.get('currency') for inv in relevant_invoices if inv.get('currency')), "$")
        return f"Based on {len(relevant_invoices)} invoice(s), the total spend is {currency_found}{total_spend:.2f}."

    if not relevant_invoices: # This will be hit if intent wasn't count/total_spend AND no invoices found
        return "I couldn't find any specific invoices matching your request in the database for context."

    context_str_parts = ["Based on the available invoice data:"]
    for inv in relevant_invoices:
        part = (f"- Inv ID {inv.get('id')}: from '{inv.get('vendor_name', 'N/A')}', "
                f"dated {inv.get('invoice_date', 'N/A')}, "
                f"total {inv.get('currency', '$')}{inv.get('total_amount', 0.0):.2f}, "
                f"status '{inv.get('status', 'N/A')}'.")
        context_str_parts.append(part)
    final_context = "\n".join(context_str_parts)
    logger.debug(f"Final context for OpenAI (len {len(final_context)}): {final_context[:500]}...")
    return final_context


@chat_bp.route("/", methods=["POST"])
def chat_with_assistant_route():
    logger.info("Chat route /api/chat/ POST request received.") 
    openai_service = current_app.extensions.get('openai_service'); db_service = current_app.extensions.get('db_service')
    logger.debug(f"OpenAI Service in chat_route: {'Available' if openai_service else 'NOT AVAILABLE'}")
    logger.debug(f"DB Service in chat_route: {'Available' if db_service else 'NOT AVAILABLE'}")
    if not openai_service: logger.error("CRITICAL: OpenAI service None."); return jsonify({"reply": "Chat assistant unavailable (OpenAI error)."}), 503 # Changed message
    data = request.json; user_message = data.get("message")
    if not user_message: logger.warning("No message provided."); return jsonify({"error": "No message"}), 400
    logger.info(f"Chat request for: '{user_message}'")
    try:
        logger.info("Step 1 (Chat Route): Getting NLU from query...")
        structured_nlu = get_structured_intent_from_query(openai_service, user_message)
        invoice_context_str = "No specific invoice context built." 
        if structured_nlu and not structured_nlu.get("error"):
            logger.info(f"NLU result: Intent='{structured_nlu.get('intent')}', Entities='{structured_nlu.get('entities')}'")
            logger.info("Step 2 (Chat Route): Building context from DB...")
            invoice_context_str = build_context_from_structured_intent(db_service, structured_nlu)
            if structured_nlu.get("intent") in ["count_invoices", "get_total_spend"] and not any(err_kw in invoice_context_str for err_kw in ["Error", "I couldn't find", "understanding the specifics", "Database service is not available"]):
                logger.info(f"Intent '{structured_nlu.get('intent')}' handled directly. Reply: {invoice_context_str}")
                return jsonify({"reply": invoice_context_str}), 200
        else: 
            logger.error(f"NLU failed or error: {structured_nlu}")
            invoice_context_str = structured_nlu.get("error", "Issue understanding request.")
            if structured_nlu and structured_nlu.get("original_nlu_response","").startswith("ERROR_OPENAI_"):
                 invoice_context_str += " AI NLU error: " + structured_nlu["original_nlu_response"]
        
        logger.info("Step 3 (Chat Route): Building messages for OpenAI main response...")
        messages_for_openai = openai_service.build_prompt_with_context(user_message, invoice_context_str)
        logger.info("Step 4 (Chat Route): Calling OpenAI for main response...")
        assistant_reply = openai_service.get_chat_completion(messages_for_openai)
        logger.info(f"RAW assistant_reply from OpenAIService: '{assistant_reply}'")
        if assistant_reply is None or assistant_reply.startswith("ERROR_") or "AI_ASSISTANT_EMPTY_REPLY" in assistant_reply:
            logger.error(f"OpenAI service error/no valid reply: {assistant_reply}")
            final_reply = "Sorry, AI issue. Try again."
            if assistant_reply:
                if "authentication" in assistant_reply.lower(): final_reply = "AI Auth Error."
                elif "rate_limit" in assistant_reply.lower(): final_reply = "AI busy. Try later."
            return jsonify({"reply": final_reply}), 500
        logger.info(f"Sending AI reply: '{assistant_reply[:100]}...'")
        return jsonify({"reply": assistant_reply}), 200
    except Exception as e:
        logger.error(f"Unhandled EXCEPTION in chat route: {e}", exc_info=True)
        return jsonify({"reply": "Unexpected internal error in chat."}), 500