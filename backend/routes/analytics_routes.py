# backend/routes/analytics_routes.py
from flask import Blueprint, jsonify, current_app, request
import logging
from datetime import datetime, timedelta # For date calculations

logger = logging.getLogger(__name__)
analytics_bp = Blueprint('analytics_bp', __name__)

@analytics_bp.route('/summary', methods=['GET'])
def get_summary_analytics():
    db_service = current_app.extensions.get('db_service')
    if not db_service:
        logger.error("DbService not initialized in analytics/summary.")
        return jsonify({"error": "Analytics service not available"}), 503
    try:
        summary = db_service.get_analytics_summary()
        return jsonify(summary), 200
    except Exception as e:
        logger.error(f"Error in /analytics/summary endpoint: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve summary analytics"}), 500

@analytics_bp.route('/expenses-by-vendor', methods=['GET'])
def get_vendor_expenses():
    db_service = current_app.extensions.get('db_service')
    if not db_service:
        logger.error("DbService not initialized in analytics/expenses-by-vendor.")
        return jsonify({"error": "Analytics service not available"}), 503
    try:
        limit = request.args.get('limit', 5, type=int) # Default to 5 for dashboard
        vendor_expenses = db_service.get_expenses_by_vendor(limit=limit)
        return jsonify(vendor_expenses), 200
    except Exception as e:
        logger.error(f"Error in /analytics/expenses-by-vendor endpoint: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve vendor expenses"}), 500

@analytics_bp.route('/expenses-by-category', methods=['GET'])
def get_category_expenses():
    db_service = current_app.extensions.get('db_service')
    if not db_service:
        logger.error("DbService not initialized in analytics/expenses-by-category.")
        return jsonify({"error": "Analytics service not available"}), 503
    try:
        limit = request.args.get('limit', 5, type=int) # Default to 5
        category_expenses = db_service.get_expenses_by_category(limit=limit)
        return jsonify(category_expenses), 200
    except Exception as e:
        logger.error(f"Error in /analytics/expenses-by-category endpoint: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve category expenses"}), 500

@analytics_bp.route('/monthly-spend', methods=['GET'])
def get_monthly_spending():
    db_service = current_app.extensions.get('db_service')
    if not db_service:
        logger.error("DbService not initialized in analytics/monthly-spend.")
        return jsonify({"error": "Analytics service not available"}), 503
    try:
        monthly_data = db_service.get_monthly_spend()
        return jsonify(monthly_data), 200
    except Exception as e:
        logger.error(f"Error in /analytics/monthly-spend endpoint: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve monthly spending data"}), 500

@analytics_bp.route('/openai-summary', methods=['GET'])
def get_openai_dashboard_summary():
    db_service = current_app.extensions.get('db_service')
    openai_service = current_app.extensions.get('openai_service')

    if not db_service or not openai_service:
        logger.error("Services not available for openai-summary.")
        return jsonify({"error": "AI summary service not available."}), 503

    try:
        # 1. Gather more comprehensive data
        overall_stats = db_service.get_comprehensive_report_summary_stats() # Gets total_invoices, total_spent, date_range, unique_vendors
        top_vendors = db_service.get_expenses_by_vendor(limit=3)
        top_categories = db_service.get_expenses_by_category(limit=3)
        monthly_trend_all = db_service.get_monthly_spend()

        # Prepare context for OpenAI
        prompt_context_parts = ["Key Overall Invoice Statistics:"]
        if overall_stats:
            prompt_context_parts.append(f"- Total Processed Invoices: {overall_stats.get('total_invoices', 0)}")
            prompt_context_parts.append(f"- Total Spend (All Time): ${overall_stats.get('total_spent', 0.0):.2f}")
            prompt_context_parts.append(f"- Data covers period from {overall_stats.get('oldest_invoice_date', 'N/A')} to {overall_stats.get('newest_invoice_date', 'N/A')}.")
            prompt_context_parts.append(f"- Number of Unique Vendors: {overall_stats.get('unique_vendors', 0)}")
        else:
            prompt_context_parts.append("- No overall statistics available.")

        if top_vendors:
            prompt_context_parts.append("\nTop Spending Vendors (All Time):")
            for v in top_vendors:
                prompt_context_parts.append(f"  - {v.get('vendor_name', 'N/A')}: ${v.get('total_spent_for_vendor', 0.0):.2f}")
        
        if top_categories:
            prompt_context_parts.append("\nTop Spending Categories (All Time):")
            for c in top_categories:
                prompt_context_parts.append(f"  - {c.get('user_category', 'Uncategorized')}: ${c.get('total_spent_for_category', 0.0):.2f}")

        if monthly_trend_all:
            # Briefly summarize trend, e.g., first and last month with data, or peak month
            first_month_data = monthly_trend_all[0] if monthly_trend_all else None
            last_month_data = monthly_trend_all[-1] if monthly_trend_all else None
            peak_month_data = max(monthly_trend_all, key=lambda x: x.get('monthly_total', 0.0)) if monthly_trend_all else None
            
            prompt_context_parts.append("\nMonthly Spending Trend Snippet:")
            if first_month_data: prompt_context_parts.append(f"  - Earliest activity in {first_month_data.get('month_year')}: ${float(first_month_data.get('monthly_total',0.0)):.2f}")
            if peak_month_data: prompt_context_parts.append(f"  - Peak spending in {peak_month_data.get('month_year')}: ${float(peak_month_data.get('monthly_total',0.0)):.2f}")
            if last_month_data and last_month_data != first_month_data and last_month_data != peak_month_data : 
                prompt_context_parts.append(f"  - Latest activity in {last_month_data.get('month_year')}: ${float(last_month_data.get('monthly_total',0.0)):.2f}")
        
        prompt_context = "\n".join(prompt_context_parts)

        # Instruction for OpenAI
        user_style_query = f"""
You are an AI financial analyst for InvoxAI. Based on the provided overall invoice statistics and spending patterns, 
generate a concise (3-5 sentences) high-level business insight summary. 
Focus on:
1. The overall scale of operations (total spend, number of invoices).
2. Key areas of expenditure (top vendors or categories).
3. Any discernible high-level trends or significant periods.
Be professional and provide a quick, informative overview. Do not list all the data again, but synthesize it.
Current date for reference is {datetime.now().strftime('%B %Y')}.
"""
        messages = openai_service.build_prompt_with_context(
            user_query=user_style_query.strip(),
            invoice_context_str=prompt_context
        )
        
        logger.info("Requesting enhanced AI summary for dashboard from OpenAI...")
        ai_summary = openai_service.get_chat_completion(messages, model="gpt-3.5-turbo", temperature=0.5, max_tokens=300)

        if ai_summary and not ai_summary.startswith("ERROR_") and "AI_ASSISTANT_EMPTY_REPLY" not in ai_summary:
            logger.info(f"Enhanced AI Summary Generated: {ai_summary[:100]}...")
            return jsonify({"ai_insight_summary": ai_summary}), 200
        else:
            # ... (error handling same as before) ...
            logger.error(f"Failed to get enhanced AI summary or OpenAI returned an error string: {ai_summary}")
            user_facing_error = "Failed to generate AI dashboard summary."
            if ai_summary and "authentication" in ai_summary.lower(): user_facing_error = "AI service authentication issue."
            elif ai_summary and "rate_limit" in ai_summary.lower(): user_facing_error = "AI service is busy, please try later."
            return jsonify({"error": user_facing_error, "details": ai_summary}), 500

    except Exception as e:
        current_app.logger.error(f"Error in /analytics/openai-summary endpoint: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve AI dashboard summary due to an internal error."}), 500