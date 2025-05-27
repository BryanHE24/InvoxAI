# backend/routes/report_routes.py
from flask import Blueprint, request, jsonify, current_app, make_response
from datetime import datetime, timedelta
import json
import logging
import markdown 
from weasyprint import HTML, CSS # Main WeasyPrint imports
# from weasyprint.fonts import FontConfiguration # <--- TEMPORARILY COMMENTED OUT FOR DEBUGGING

logger = logging.getLogger(__name__)
report_bp = Blueprint('report_bp', __name__)

def format_invoices_for_monthly_report_context(invoices, report_month_year_str, report_filters):
    """
    Formats a list of invoice data into a string suitable for an OpenAI prompt
    to generate a monthly expense report.
    """
    if not invoices:
        return f"No processed invoices found for {report_month_year_str} matching the criteria: {report_filters if report_filters else 'None'}."

    report_context_parts = [f"Invoice Data for Monthly Expense Report - {report_month_year_str}:"]
    if report_filters.get('vendor_name'):
        report_context_parts[0] += f" (Filtered by Vendor: {report_filters['vendor_name']})"
    if report_filters.get('category'):
        report_context_parts[0] += f" (Filtered by Category: {report_filters['category']})"
    
    total_spend_for_month = sum(float(inv.get('total_amount', 0.0) or 0.0) for inv in invoices)
    
    # Details for individual invoices in the prompt
    for inv_idx, inv in enumerate(invoices): 
        if inv_idx < 15: # Limit details in prompt to keep it manageable
            report_context_parts.append(
                f"\n- Inv ID {inv.get('id')}: From '{inv.get('vendor_name', 'N/A')}', Date: {inv.get('invoice_date', 'N/A')}, "
                f"Total: {inv.get('currency', '$')}{float(inv.get('total_amount', 0.0) or 0.0):.2f}, Category: '{inv.get('user_category', 'N/A')}'"
            )
            # Add 1-2 key line items if available and parsed
            if inv.get('line_items') and isinstance(inv['line_items'], list) and inv['line_items']:
                key_items = []
                for item_li_idx, item_li in enumerate(inv['line_items'][:2]): # Max 2 line items per invoice for prompt
                    desc = item_li.get('description', 'Item')[:40] # Truncate long descriptions
                    amt = float(item_li.get('amount', 0.0) or 0.0)
                    key_items.append(f"{desc} ({inv.get('currency', '$')}{amt:.2f})")
                if key_items:
                    report_context_parts.append(f"    Key Items: {'; '.join(key_items)}")
        elif inv_idx == 15: # Note if we truncated the detailed list for the prompt
             report_context_parts.append("\n... (additional individual invoice details truncated for prompt brevity)")
             break # Stop adding more individual invoice details to the prompt
    
    # Add overall summary of the provided data to the context
    report_context_parts.append(f"\nSummary of provided data for {report_month_year_str}: {len(invoices)} invoices, total spend ${total_spend_for_month:.2f}.")
    full_context = "\n".join(report_context_parts)
    
    MAX_CONTEXT_CHARS = 12000 
    if len(full_context) > MAX_CONTEXT_CHARS:
        logger.warning(f"Monthly report context length ({len(full_context)}) for OpenAI prompt truncated to {MAX_CONTEXT_CHARS} characters.")
        full_context = full_context[:MAX_CONTEXT_CHARS] + "\n... (Context truncated due to length limitation for AI prompt)"
    return full_context


@report_bp.route('/generate/monthly-expense', methods=['POST', 'OPTIONS'])
def generate_monthly_expense_report():
    if request.method == 'OPTIONS': return jsonify(success=True), 200 # Handle CORS preflight

    db_service = current_app.extensions.get('db_service')
    openai_service = current_app.extensions.get('openai_service')
    if not db_service or not openai_service: 
        logger.error("generate_monthly_expense_report: DbService or OpenAIService not available.")
        return jsonify({"error": "Reporting service unavailable due to server configuration."}), 503

    data = request.get_json();
    if not data: return jsonify({"error": "Missing request data (year, month)."}), 400
    try:
        year = int(data.get('year')); month = int(data.get('month'))
        if not (2000 <= year <= datetime.now().year + 10 and 1 <= month <= 12):
            return jsonify({"error": "Invalid year or month provided."}), 400
    except (ValueError, TypeError): 
        return jsonify({"error": "Year and month must be valid integers."}), 400
    
    vendor_filter = data.get('vendor_name'); category_filter = data.get('category')
    report_month_year_str = datetime(year, month, 1).strftime('%B %Y')
    report_filters_for_log = {"vendor": vendor_filter, "category": category_filter}
    logger.info(f"Generating monthly expense report content for: {report_month_year_str}, Filters: {report_filters_for_log}")

    try:
        invoices_for_report = db_service.get_invoices_for_report(year, month, vendor_filter, category_filter, limit_for_details=100) # Fetch more for context
        
        if not invoices_for_report:
            logger.info(f"No invoices found for monthly report: {report_month_year_str}, Filters: {report_filters_for_log}")
            no_data_md = f"# Monthly Expense Report - {report_month_year_str}\n\nNo processed invoices found for this period matching the specified criteria."
            if vendor_filter: no_data_md += f"\n**Vendor Filter:** {vendor_filter}"
            if category_filter: no_data_md += f"\n**Category Filter:** {category_filter}"
            return jsonify({"report_markdown": no_data_md, "message": "No data found to generate this report."}), 200

        report_data_context = format_invoices_for_monthly_report_context(invoices_for_report, report_month_year_str, report_filters_for_log)
        
        report_generation_prompt_instruction = f"""
Generate a professional "Monthly Expense Report" in Markdown format for InvoxAI.
Report Period: {report_month_year_str}
{f"Filters Applied: Vendor='{vendor_filter}'" if vendor_filter else ""} {f"Category='{category_filter}'" if category_filter else ""}

Report Sections (use Markdown headings e.g., ## Section Title, ### Sub-Section, bold, lists, and tables where appropriate):
1.  **Executive Summary:** (3-5 sentences) Briefly summarize total spending, number of invoices processed, key vendors or categories that stand out, and any notable trends or observations for the month based *only* on the data provided in the <report_data_context>. If comparing to previous periods, explicitly state if context for such comparison is missing.
2.  **Spending Overview:** Clearly state the total number of invoices included in this report period and the total amount spent.
3.  **Top Vendors by Spend:** (If vendor data exists in context) Present as a Markdown table: | Vendor | Total Spent | # Invoices |. List the top 3-5 vendors from the context. Add a brief sentence summarizing vendor activity.
4.  **Spend by Category:** (If category data exists in context) Present as a Markdown table: | Category | Total Spent | # Invoices |. List the top 3-5 categories from the context. Add a brief sentence summarizing category spending.
5.  **Invoice Detail Summary (Appendix):** List key details (ID, Vendor, Date, Total Amount, Category) for up to 10-15 individual invoices from the provided context. If more invoices were in the context than are listed for brevity, note that.

Important Instructions:
- Be strictly data-driven. Your entire report must be based *only* on the information within the <report_data_context> below.
- Do NOT invent or assume any data not explicitly present in the context.
- If data for a specific section or sub-section is missing or insufficient from the context, clearly state "Insufficient data for this section" or "Data not available".
- Maintain a professional and analytical tone.
- Ensure all monetary values are formatted clearly (e.g., $1,234.56 or £600.00, using the currency from the data if provided, otherwise default to USD $).

<report_data_context>
{report_data_context}
</report_data_context>

Generate the full Markdown report now.
"""
        messages = [{"role": "user", "content": report_generation_prompt_instruction.strip()}]
        logger.info(f"Requesting Monthly Report Markdown from OpenAI for {report_month_year_str} (prompt length: {len(report_generation_prompt_instruction)} chars)...")
        report_markdown = openai_service.get_chat_completion(messages, model="gpt-3.5-turbo-0125", temperature=0.2, max_tokens=3000) 
        
        if report_markdown and not report_markdown.startswith("ERROR_") and "AI_ASSISTANT_EMPTY_REPLY" not in report_markdown:
            logger.info(f"Markdown report generated successfully for {report_month_year_str}. Length: {len(report_markdown)}")
            cleaned_md = report_markdown.strip();
            if cleaned_md.startswith("```markdown"): cleaned_md = cleaned_md[10:]
            if cleaned_md.startswith("```"): cleaned_md = cleaned_md[3:]
            if cleaned_md.endswith("```"): cleaned_md = cleaned_md[:-3]
            return jsonify({"report_markdown": cleaned_md.strip(), "message": "Report content generated successfully."}), 200
        else:
            logger.error(f"Failed to generate report markdown from OpenAI for {report_month_year_str}: {report_markdown}")
            return jsonify({"error": "Failed to generate report content via AI.", "details": report_markdown}), 500
    except Exception as e:
        logger.error(f"Error generating monthly expense report content: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred while generating the report content."}), 500


@report_bp.route('/generate/comprehensive-overview', methods=['POST', 'OPTIONS'])
def generate_comprehensive_overview_report():
    if request.method == 'OPTIONS': return jsonify(success=True), 200
    db_service = current_app.extensions.get('db_service'); openai_service = current_app.extensions.get('openai_service')
    if not db_service or not openai_service: return jsonify({"error": "Reporting service unavailable."}), 503
    logger.info("Generating Comprehensive Overview Report...")
    try:
        overall_summary = db_service.get_comprehensive_report_summary_stats() 
        all_vendor_spend = db_service.get_expenses_by_vendor(limit=None) 
        all_category_spend = db_service.get_expenses_by_category(limit=None)
        monthly_spend_trend = db_service.get_monthly_spend() 
        status_counts = db_service.get_invoice_status_counts() 
        context_parts = ["<report_data_context>"]
        context_parts.append("\n[Overall Financial Metrics]")
        if overall_summary:
            context_parts.append(f"Total Processed Invoices: {overall_summary.get('total_invoices', 'N/A')}"); context_parts.append(f"Total Amount Spent (Processed): ${float(overall_summary.get('total_spent', 0.0)):.2f}"); context_parts.append(f"Average Spend per Invoice: ${float(overall_summary.get('total_spent', 0.0) / (overall_summary.get('total_invoices', 1) or 1)):.2f}"); context_parts.append(f"Date Range: {overall_summary.get('oldest_invoice_date', 'N/A')} to {overall_summary.get('newest_invoice_date', 'N/A')}"); context_parts.append(f"Unique Vendors: {overall_summary.get('unique_vendors', 'N/A')}")
        else: context_parts.append("Overall financial metrics could not be calculated.")
        context_parts.append("\n[Spending by Category (All Time - Top 7 for context)]") # Clarified title
        if all_category_spend:
            for cat_data in all_category_spend[:7]: context_parts.append(f"- Category: {cat_data.get('user_category', 'N/A')}, Total Spent: ${float(cat_data.get('total_spent_for_category', 0.0)):.2f}, Number of Invoices: {cat_data.get('invoice_count', 0)}")
            if len(all_category_spend) > 7: context_parts.append("  ...and more categories exist.")
        else: context_parts.append("No categorized spending data available.")
        context_parts.append("\n[Spending by Vendor (All Time - Top 7 for context)]") # Clarified title
        if all_vendor_spend:
            for ven_data in all_vendor_spend[:7]: context_parts.append(f"- Vendor: {ven_data.get('vendor_name', 'N/A')}, Total Spent: ${float(ven_data.get('total_spent_for_vendor', 0.0)):.2f}, Number of Invoices: {ven_data.get('invoice_count', 0)}")
            if len(all_vendor_spend) > 7: context_parts.append("  ...and more vendors exist.")
        else: context_parts.append("No vendor spending data available.")
        context_parts.append("\n[Monthly Spending Trend (All Time - Last 12 months for context)]") # Clarified title
        if monthly_spend_trend:
            for month_data in monthly_spend_trend[-12:]: context_parts.append(f"- Month: {month_data.get('month_year', 'N/A')}, Total Spent: ${float(month_data.get('monthly_total', 0.0)):.2f}, Number of Invoices: {month_data.get('invoice_count',0)}")
            if len(monthly_spend_trend) > 12 : context_parts.append("  ... (trend data also available for earlier periods)")
        else: context_parts.append("No monthly spending trend data available.")
        context_parts.append("\n[Invoice Processing Status (All Invoices in System)]") # Clarified title
        if status_counts:
            for status_key, count_val in status_counts.items(): context_parts.append(f"- {status_key.replace('_', ' ').title()}: {count_val}")
        else: context_parts.append("Could not retrieve invoice status counts.")
        context_parts.append("</report_data_context>"); report_data_context = "\n".join(context_parts)
        MAX_CONTEXT_CHARS = 12000 
        if len(report_data_context) > MAX_CONTEXT_CHARS: logger.warning(f"Comprehensive report context length ({len(report_data_context)}) truncated."); report_data_context = report_data_context[:MAX_CONTEXT_CHARS] + "\n... (Context truncated)"
        report_master_prompt = f"""
You are InvoxAI's advanced financial reporting engine. Generate a "Comprehensive Invoice Overview Report" in Markdown.
This report covers all processed invoice data available in the system.
Report Sections (use Markdown headings ##, ###, bold, lists, tables where appropriate):
1.  **Executive Summary:** (4-6 sentences) High-level overview of total spending, number of invoices, key spending drivers (top categories/vendors), and any significant overall trends or observations from the *entire provided dataset*.
2.  **Key Financial Metrics (Overall):** Present the data from <overall_financial_metrics> clearly.
3.  **Detailed Spending Analysis:**
    *   **Spending by Category (All Time):** Summarize insights from <top_categories_data>. Present a Markdown table for the top categories if data is rich.
    *   **Spending by Vendor (All Time):** Summarize insights from <top_vendors_data>. Present a Markdown table for the top vendors if data is rich.
4.  **Spending Trends Over Time:** Analyze and describe patterns from <monthly_spending_trend_data>.
5.  **Invoice Processing Status:** Summarize the data from <invoice_status_summary>.
6.  **Concluding Insights & Recommendations (Optional):** Based *only* on the data, offer 1-2 concluding thoughts or potential areas for review. Do not make business recommendations if data is insufficient.
Be strictly data-driven. If data for a section is missing or insufficient from the context, state "Data not available" or "Insufficient data". Use a professional, analytical tone. Ensure monetary values are clear.
Here is the full data context to use:
{report_data_context}
Generate the complete Markdown report."""
        messages = [{"role": "user", "content": report_master_prompt.strip()}]
        logger.info("Requesting Comprehensive Overview Report Markdown from OpenAI...")
        report_markdown = openai_service.get_chat_completion(messages, model="gpt-4-turbo-preview", temperature=0.3, max_tokens=3500) 
        if report_markdown and not report_markdown.startswith("ERROR_") and "AI_ASSISTANT_EMPTY_REPLY" not in report_markdown:
            logger.info(f"Comprehensive report generated. Length: {len(report_markdown)}")
            cleaned_md = report_markdown.strip();
            if cleaned_md.startswith("```markdown"): cleaned_md = cleaned_md[10:]
            if cleaned_md.startswith("```"): cleaned_md = cleaned_md[3:]
            if cleaned_md.endswith("```"): cleaned_md = cleaned_md[:-3]
            return jsonify({"report_markdown": cleaned_md.strip(), "message": "Comprehensive report generated."}), 200
        else:
            logger.error(f"Failed to generate comprehensive report from OpenAI: {report_markdown}")
            return jsonify({"error": "Failed to generate comprehensive report via AI.", "details": report_markdown}), 500
    except Exception as e:
        logger.error(f"Error generating comprehensive overview report: {e}", exc_info=True)
        return jsonify({"error": "Internal server error generating comprehensive report."}), 500

@report_bp.route('/export/monthly-expense/pdf', methods=['POST', 'OPTIONS'])
def export_monthly_expense_report_pdf():
    if request.method == 'OPTIONS':
        return jsonify(success=True), 200

    logger.info("PDF Export for monthly report requested.")
    
    # --- WeasyPrint logic is now active ---
    db_service = current_app.extensions.get('db_service')
    openai_service = current_app.extensions.get('openai_service')
    if not db_service or not openai_service:
        return jsonify({"error": "Reporting service unavailable for PDF export."}), 503

    data = request.get_json()
    if not data: return jsonify({"error": "Missing request data for PDF export."}), 400
    try:
        year = int(data.get('year')); month = int(data.get('month'))
        if not (2000 <= year <= datetime.now().year + 10 and 1 <= month <= 12):
            return jsonify({"error": "Invalid year or month for PDF export."}), 400
    except (ValueError, TypeError): 
        return jsonify({"error": "Year and month must be valid integers for PDF export."}), 400
    
    vendor_filter = data.get('vendor_name'); category_filter = data.get('category')
    report_month_year_str_fn = datetime(year, month, 1).strftime('%Y_%m_%B') 
    filename = f"InvoxAI_Monthly_Expense_Report_{report_month_year_str_fn}"
    if vendor_filter: filename += f"_Vendor_{vendor_filter.replace(' ', '_').lower()}"
    if category_filter: filename += f"_Category_{category_filter.replace(' ', '_').lower()}"
    filename += ".pdf"

    report_markdown_content = None
    try: 
        logger.info(f"PDF Export: Generating Markdown for Monthly Report - {datetime(year,month,1).strftime('%B %Y')}")
        invoices_for_report = db_service.get_invoices_for_report(year, month, vendor_filter, category_filter, limit_for_details=100)
        
        # Use a simpler context/prompt if no invoices found, directly for markdown
        if not invoices_for_report: 
            report_markdown_content = f"# Monthly Expense Report - {datetime(year,month,1).strftime('%B %Y')}\n\n"
            if vendor_filter: report_markdown_content += f"**Vendor Filter:** {vendor_filter}\n"
            if category_filter: report_markdown_content += f"**Category Filter:** {category_filter}\n"
            report_markdown_content += "\nNo processed invoices found for this period matching the specified criteria."
        else:
            report_data_context = format_invoices_for_monthly_report_context(invoices_for_report, datetime(year,month,1).strftime('%B %Y'), {"vendor_name": vendor_filter, "category": category_filter})
            report_generation_prompt_instruction = f"""
Generate a professional "Monthly Expense Report" in Markdown format for InvoxAI. Report Period: {datetime(year,month,1).strftime('%B %Y')}
{f"Filters Applied: Vendor='{vendor_filter}'" if vendor_filter else ""} {f"Category='{category_filter}'" if category_filter else ""}
Sections (use Markdown headings ##, ###, bold, lists, tables): Executive Summary, Spending Overview, Top Vendors, Spend by Category, Invoice Detail Summary (Appendix).
Be strictly data-driven from <report_data_context>. If data for a section isn't there, state "Insufficient data".
<report_data_context>
{report_data_context}
</report_data_context>
Generate the full Markdown report."""
            messages = [{"role": "user", "content": report_generation_prompt_instruction.strip()}]
            report_markdown_content = openai_service.get_chat_completion(messages, model="gpt-3.5-turbo-0125", temperature=0.2, max_tokens=3000)
            
            if report_markdown_content and not report_markdown_content.startswith("ERROR_") and "AI_ASSISTANT_EMPTY_REPLY" not in report_markdown_content:
                cleaned_md = report_markdown_content.strip(); 
                if cleaned_md.startswith("```markdown"): cleaned_md = cleaned_md[10:]
                if cleaned_md.startswith("```"): cleaned_md = cleaned_md[3:]
                if cleaned_md.endswith("```"): cleaned_md = cleaned_md[:-3]
                report_markdown_content = cleaned_md.strip()
            else: 
                logger.error(f"PDF Export: AI content generation failed with: {report_markdown_content}")
                raise Exception(f"AI content generation failed for PDF: {report_markdown_content or 'Unknown AI error'}")
                
    except Exception as e: 
        logger.error(f"PDF Export: Error generating report markdown: {e}", exc_info=True)
        return jsonify({"error": "Internal error generating report content for PDF."}), 500

    if not report_markdown_content: # Should be caught by the exception above ideally
        logger.error("PDF Export: Report markdown content is unexpectedly None after generation attempt.")
        return jsonify({"error": "Could not generate report content for PDF (content was empty)."}), 500
    
    try:
        logger.info("PDF Export: Converting Markdown to HTML for WeasyPrint.")
        html_content = markdown.markdown(report_markdown_content, extensions=['tables', 'fenced_code', 'sane_lists'])
        
        pdf_css_string = """
        @page { size: A4; margin: 1.5cm; @bottom-center { content: "Page " counter(page) " of " counter(pages); font-size: 9pt; color: #666;}}
        body { font-family: 'Times New Roman', Times, serif; font-size: 11pt; line-height: 1.5; color: #222; }
        h1, h2, h3, h4, h5, h6 { font-family: 'Arial Black', 'Arial Bold', Gadget, sans-serif; color: #1a3b5c; margin-top: 1.2em; margin-bottom: 0.6em; border-bottom: 1px solid #cccccc; padding-bottom: 0.2em; page-break-after: avoid; }
        h1 { font-size: 22pt; text-align: center; border-bottom: 2px solid #1a3b5c; margin-bottom: 1em;}
        h2 { font-size: 16pt; } h3 { font-size: 13pt; } h4 { font-size: 11pt; font-style: italic; border-bottom: none;}
        table { border-collapse: collapse; width: 100%; margin-bottom: 1.2em; page-break-inside: auto; }
        tr { page-break-inside: avoid; page-break-after: auto; }
        thead { display: table-header-group; } 
        th, td { border: 1px solid #bfbfbf; padding: 7px; text-align: left; vertical-align: top; }
        th { background-color: #e9eff5; font-weight: bold; color: #1a3b5c;}
        p { margin-bottom: 0.8em; text-align: justify;}
        ul, ol { margin-bottom: 0.8em; padding-left: 25px; page-break-inside: auto; }
        li { margin-bottom: 0.3em; }
        strong, b { font-weight: bold; } em, i { font-style: italic; }
        a { color: #0066cc; text-decoration: none; } a:hover { text-decoration: underline; }
        pre { background-color: #f8f8f8; padding: 10px; border: 1px solid #eee; border-radius: 3px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; font-family: 'Courier New', monospace; font-size: 9pt;}
        code { font-family: 'Courier New', monospace; background-color: #f0f0f0; padding: 1px 3px; border-radius: 2px;}
        blockquote { border-left: 3px solid #adb5bd; padding-left: 12px; color: #495057; margin-left: 0; font-style: italic;}
        """
        
        font_config = FontConfiguration() # Using default font configuration
        html_doc = HTML(string=f"<html><head><meta charset='utf-8'><title>{filename.replace('.pdf','')}</title></head><body>{html_content}</body></html>", base_url=".")
        css_doc = CSS(string=pdf_css_string, font_config=font_config)
        
        pdf_bytes = html_doc.write_pdf(stylesheets=[css_doc], font_config=font_config)
        
        logger.info(f"PDF generated successfully for {filename}. Size: {len(pdf_bytes)} bytes.")

        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except NameError as ne: 
        logger.error(f"WeasyPrint components (HTML, CSS) not available. Error: {ne}", exc_info=True)
        return jsonify({"error": "PDF generation service component missing. Please check server logs.", "details": str(ne)}), 500
    except Exception as e:
        logger.error(f"Error generating PDF for {filename}: {e}", exc_info=True)
        error_detail = str(e)
        if "DLL load failed" in error_detail or "library not found" in error_detail.lower() or "No module named 'pangocffi'" in error_detail or "No module named '_weasyprint_bindings'" in error_detail:
            error_detail = "A required system library for PDF generation is missing or WeasyPrint installation is incomplete. Please check WeasyPrint system dependencies (e.g., Pango, Cairo, CFFI related libs)."
        return jsonify({"error": "Failed to generate PDF due to an internal error.", "details": error_detail}), 500