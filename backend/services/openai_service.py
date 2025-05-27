# backend/services/openai_service.py
from openai import OpenAI 
import httpx # Ensure httpx is imported
import logging
import json 

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self, app_config):
        self.config = app_config
        self.api_key = self.config.get('OPENAI_API_KEY')
        
        if not self.api_key or self.api_key == 'sk-YOUR_ACTUAL_OPENAI_API_KEY_HERE':
            logger.error("OpenAIService __init__: OPENAI_API_KEY not found or is placeholder in configuration.")
            raise ValueError("OpenAIService: OPENAI_API_KEY is required and valid but not configured.") 
        
        try:
            logger.info("OpenAIService __init__: Attempting to create httpx.Client with proxy=None.")
            # *** THIS IS THE KEY CHANGE: proxy (singular) instead of proxies (plural) ***
            custom_http_client = httpx.Client(proxy=None) 
            logger.info("OpenAIService __init__: httpx.Client(proxy=None) created successfully.")
            
            self.client = OpenAI(
                api_key=self.api_key,
                http_client=custom_http_client 
            )
            logger.info("OpenAIService __init__: OpenAI client CREATED successfully using custom httpx client with proxy=None.")
        except TypeError as te: 
            logger.error(f"OpenAIService __init__: TypeError during OpenAI client init: {te}", exc_info=True)
            logger.error("This might indicate an issue with httpx version or OpenAI library's http_client compatibility.")
            # Fallback: Try initializing OpenAI client without explicit http_client
            # This relies on OpenAI library's internal httpx handling and unsetting proxy ENV VARS
            logger.warning("OpenAIService __init__: Falling back to default OpenAI client initialization (ensure proxy ENV VARS are unset).")
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAIService __init__: Fallback default OpenAI client CREATED successfully.")
            except Exception as e_fallback:
                logger.error(f"OpenAIService __init__: Fallback default OpenAI client init also FAILED: {e_fallback}", exc_info=True)
                raise ValueError(f"OpenAIService: Failed to initialize OpenAI client (default and custom attempts failed) - {str(e_fallback)}")
        except Exception as e:
            logger.error(f"OpenAIService __init__: General failure to initialize OpenAI client: {e}", exc_info=True)
            raise ValueError(f"OpenAIService: Failed to initialize OpenAI client - {str(e)}")

    def get_chat_completion(self, messages, model="gpt-3.5-turbo", temperature=0.7, max_tokens=1000):
        # ... (rest of the get_chat_completion method remains THE SAME) ...
        logger.info("OpenAIService: Attempting get_chat_completion.")
        if not self.client:
            logger.error("OpenAIService: OpenAI client is not initialized in get_chat_completion.")
            return "ERROR_OPENAI_CLIENT_NOT_INITIALIZED"
        try:
            logger.debug(f"OpenAIService: Sending request to OpenAI API. Model: {model}. Messages count: {len(messages)}.")
            try:
                messages_log_str = json.dumps([{"role": m["role"], "content": m["content"][:100] + "..." if len(m["content"]) > 100 else m["content"]} for m in messages], indent=2)
                logger.debug(f"OpenAIService: Messages being sent (content truncated if long):\n{messages_log_str}")
            except Exception as log_e:
                logger.warning(f"OpenAIService: Could not serialize messages for detailed logging: {log_e}")
                logger.debug(f"OpenAIService: First user message content snippet: {next((m['content'] for m in messages if m['role'] == 'user'), 'N/A')[:100]}")
            completion = self.client.chat.completions.create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
            logger.debug(f"OpenAIService: Full OpenAI API response object: {completion.model_dump_json(indent=2)}")
            if completion.choices and len(completion.choices) > 0 and completion.choices[0].message:
                assistant_reply = completion.choices[0].message.content; token_usage = completion.usage 
                prompt_tokens = token_usage.prompt_tokens if token_usage else 'N/A'; completion_tokens = token_usage.completion_tokens if token_usage else 'N/A'; total_tokens = token_usage.total_tokens if token_usage else 'N/A'
                logger.info(f"OpenAIService: Received reply from OpenAI. Tokens: Prompt={prompt_tokens}, Completion={completion_tokens}, Total={total_tokens}")
                if assistant_reply and assistant_reply.strip():
                    logger.debug(f"OpenAIService: Assistant reply snippet: {assistant_reply.strip()[:200]}...")
                    return assistant_reply.strip()
                else:
                    logger.warning("OpenAIService: Assistant's message content from OpenAI was None or empty.")
                    return "AI_ASSISTANT_EMPTY_REPLY: I received a response, but it was empty. Can you try rephrasing?"
            else:
                logger.error("OpenAIService: OpenAI response structure unexpected or no choices/message found.")
                return "ERROR_OPENAI_NO_CHOICES: I'm sorry, I couldn't interpret the AI's response structure."
        except Exception as e: 
            logger.error(f"OpenAIService: Exception calling OpenAI chat completions API: {e}", exc_info=True)
            error_message_lower = str(e).lower()
            if "authentication" in error_message_lower: return "ERROR_OPENAI_AUTHENTICATION: OpenAI Authentication Error..."
            elif "rate_limit_exceeded" in error_message_lower or "rate limit" in error_message_lower: return "ERROR_OPENAI_RATE_LIMIT: The AI assistant is too busy..."
            elif "context_length_exceeded" in error_message_lower: return "ERROR_OPENAI_CONTEXT_TOO_LONG: Your request or the conversation is too long..."
            elif "invalid_request_error" in error_message_lower: return f"ERROR_OPENAI_INVALID_REQUEST: Issue with the request to AI: {str(e)[:150]}"
            return f"ERROR_OPENAI_API_CALL_FAILED: An error occurred with the AI assistant: {str(e)[:150]}"

    def build_prompt_with_context(self, user_query, invoice_context_str=""):
        # ... (this method remains THE SAME) ...
        system_message = "You are InvoxAI..." # Keep your detailed system message
        messages = [{"role": "system", "content": system_message.strip()}]
        if invoice_context_str and invoice_context_str.strip() and "No specific invoice data found" not in invoice_context_str and "Database service is not available" not in invoice_context_str:
            context_prompt = f"Here is some potentially relevant invoice data...\n<invoice_data_context>\n{invoice_context_str}\n</invoice_data_context>\n"
            messages.append({"role": "system", "content": context_prompt.strip()}) 
        elif not invoice_context_str or "No specific invoice data found" in invoice_context_str:
            messages.append({"role": "system", "content": "No specific invoice context was retrieved..."})
        messages.append({"role": "user", "content": user_query})
        logger.debug(f"Constructed messages for OpenAI call: {json.dumps(messages, indent=2)}")
        return messages