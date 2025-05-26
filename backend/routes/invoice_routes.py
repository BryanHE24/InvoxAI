# backend/routes/invoice_routes.py
from flask import Blueprint, request, jsonify, current_app
import os
import uuid 
import json 
from decimal import Decimal
import datetime # Import datetime to check for date/datetime objects

invoice_bp = Blueprint('invoice_bp', __name__)

# Helper function to format invoice data for JSON response
def format_invoice_for_json(invoice_dict):
    if not invoice_dict:
        return None
    
    formatted_invoice = {}
    for key, value in invoice_dict.items():
        if isinstance(value, Decimal):
            formatted_invoice[key] = float(value)
        elif key in ['invoice_date', 'due_date'] and isinstance(value, datetime.date):
            formatted_invoice[key] = value.isoformat() # YYYY-MM-DD
        elif isinstance(value, datetime.datetime): 
            formatted_invoice[key] = value.isoformat() 
        else:
            formatted_invoice[key] = value
            
    if 'line_items' in formatted_invoice and formatted_invoice['line_items']:
        try:
            line_items_data = json.loads(formatted_invoice['line_items']) if isinstance(formatted_invoice['line_items'], str) else formatted_invoice['line_items']
            if isinstance(line_items_data, list):
                def convert_line_item_decimals(item):
                    if isinstance(item, dict):
                        for k_li, v_li in item.items():
                            if isinstance(v_li, Decimal): item[k_li] = float(v_li)
                    return item
                formatted_invoice['line_items'] = [convert_line_item_decimals(li) for li in line_items_data]
            elif line_items_data is not None: # If it's not a list but also not None (e.g. a single object wrongly stored)
                 current_app.logger.warning(f"line_items for invoice ID {invoice_dict.get('id')} is not a list after JSON load: {type(line_items_data)}")
                 formatted_invoice['line_items'] = [] # Default to empty list
            else: # if line_items_data is None
                 formatted_invoice['line_items'] = []


        except (json.JSONDecodeError, TypeError) as e:
            current_app.logger.warning(f"Could not parse/process line_items for jsonify for invoice {invoice_dict.get('id')}: {e}")
            formatted_invoice['line_items'] = [] # Default to empty list if error

    return formatted_invoice


@invoice_bp.route("/upload", methods=["POST"])
def upload_invoice_route():
    db_service = current_app.extensions.get('db_service')
    s3_service = current_app.extensions.get('s3_service')
    textract_service = current_app.extensions.get('textract_service')

    if not all([db_service, s3_service, textract_service]):
        current_app.logger.error("One or more services not available in /upload route.")
        return jsonify({"error": "Server configuration error, services not available."}), 503
       
    current_app.logger.info("Upload endpoint hit")
    if 'file' not in request.files:
        current_app.logger.error("No file part in request")
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        current_app.logger.error("No selected file")
        return jsonify({"error": "No selected file"}), 400

    original_filename = file.filename
    current_app.logger.info(f"File received: {original_filename}")
    
    invoice_record = None
    try:
        invoice_record = db_service.create_invoice_record(
            original_filename=original_filename,
            status='pending_s3_upload'
        )
        if not invoice_record or 'id' not in invoice_record:
            current_app.logger.error(f"Failed to create database record for {original_filename}")
            return jsonify({"error": "Failed to initialize invoice processing in DB"}), 500
        invoice_id = invoice_record['id']
        current_app.logger.info(f"Initial DB record created for {original_filename} with ID: {invoice_id}")

        s3_folder = f"invoices/{invoice_id}"
        s3_object_key = s3_service.upload_file_obj(file_obj=file, object_name=original_filename, folder=s3_folder)
        if not s3_object_key:
            db_service.update_invoice_status(invoice_id, status='s3_upload_failed', error_message="S3 upload failed")
            return jsonify({"error": "Failed to upload file to S3 storage."}), 500
        current_app.logger.info(f"File {original_filename} uploaded to S3 at {s3_service.bucket_name}/{s3_object_key}")

        update_s3_success = db_service.update_invoice_s3_details(
            invoice_id=invoice_id,
            s3_bucket=s3_service.bucket_name,
            s3_key=s3_object_key,
            status='pending_textract_submission'
        )
        if not update_s3_success:
            current_app.logger.error(f"Failed to update DB with S3 details for invoice ID {invoice_id}.")
            return jsonify({"error": "File uploaded to S3, but failed to update database record with S3 info."}), 500
        current_app.logger.info(f"DB record updated for invoice ID {invoice_id} with S3 details.")

        client_request_token = f"invox-{invoice_id}-{str(uuid.uuid4())}" 
        job_tag = f"InvoxAI-Invoice-{invoice_id}"
        
        textract_job_id = textract_service.start_expense_analysis(
            s3_object_key=s3_object_key,
            client_request_token=client_request_token,
            job_tag=job_tag
        )
        if not textract_job_id:
            db_service.update_invoice_status(invoice_id, status='textract_submission_failed', error_message="Failed to start Textract expense analysis job.")
            return jsonify({"error": "Failed to start Textract analysis."}), 500
        current_app.logger.info(f"Textract Expense Analysis started for invoice ID {invoice_id}. JobId: {textract_job_id}")

        update_textract_job_success = db_service.update_invoice_status(
            invoice_id,
            status='processing_textract',
            textract_job_id=textract_job_id
        )
        if not update_textract_job_success:
            current_app.logger.error(f"Failed to update DB with Textract Job ID for invoice {invoice_id}.")
            return jsonify({"error": "Textract job started, but failed to update database record with Job ID."}), 500
        current_app.logger.info(f"DB record updated for invoice ID {invoice_id} with Textract JobId: {textract_job_id}, status 'processing_textract'.")
        
        return jsonify({
            "message": f"File '{original_filename}' uploaded and Textract Expense Analysis initiated.",
            "invoice_id": invoice_id,
            "s3_bucket": s3_service.bucket_name,
            "s3_key": s3_object_key,
            "textract_job_id": textract_job_id,
            "current_status": 'processing_textract'
        }), 202
            
    except Exception as e:
        current_app.logger.error(f"Critical error during upload process for {original_filename}: {e}", exc_info=True)
        db_service = current_app.extensions.get('db_service') 
        if db_service and invoice_record and 'id' in invoice_record:
             db_service.update_invoice_status(invoice_record['id'], status='error', error_message=f"Upload processing error: {str(e)[:250]}")
        return jsonify({"error": "An internal error occurred during file upload processing."}), 500
    
    return jsonify({"error": "File upload failed due to an unknown server issue"}), 500

@invoice_bp.route("/<int:invoice_id>/process-textract-result", methods=["POST"])
def process_textract_result_route(invoice_id):
    db_service = current_app.extensions.get('db_service')
    textract_service = current_app.extensions.get('textract_service')
    if not all([db_service, textract_service]):
        current_app.logger.error("One or more services not available in /process-textract-result route.")
        return jsonify({"error": "Server configuration error, services not available."}), 503

    current_app.logger.info(f"Attempting to process Textract Expense result for invoice ID: {invoice_id}")
    invoice = db_service.get_invoice_by_id(invoice_id)
    if not invoice: return jsonify({"error": "Invoice not found"}), 404
    textract_job_id = invoice.get('textract_job_id')
    current_db_status = invoice.get('status')
    if not textract_job_id: return jsonify({"error": "No Textract Job ID found."}), 400
    if current_db_status in ['processed', 'textract_failed', 'parsing_failed', 'db_update_failed_post_textract']:
        return jsonify({"message": f"Invoice already processed or failed: {current_db_status}", "data": format_invoice_for_json(invoice)}), 200
    
    current_app.logger.info(f"Fetching Textract Expense results for Job ID: {textract_job_id} (Invoice ID: {invoice_id})")
    textract_response = textract_service.get_all_expense_results_paginated(textract_job_id)
    actual_job_status_from_textract = textract_response.get('JobStatus')
    current_app.logger.info(f"Textract Expense Job Status for {textract_job_id} from AWS: {actual_job_status_from_textract}")

    if actual_job_status_from_textract == 'SUCCEEDED':
        expense_docs = textract_response.get('ExpenseDocuments', [])
        if not expense_docs:
            db_service.update_invoice_status(invoice_id, status='textract_failed', error_message="SUCCEEDED with no ExpenseDocuments")
            return jsonify({"error": "Textract analysis SUCCEEDED but no expense documents returned."}), 500
        try:
            current_app.logger.info(f"Parsing {len(expense_docs)} ExpenseDocument(s) from Textract for invoice ID {invoice_id}")
            parsed_data = textract_service.parse_expense_data(expense_docs)
            
            # Pass parsed_data dictionary directly to update_invoice_parsed_data
            # The DbService method will handle which fields to use.
            update_db_success = db_service.update_invoice_parsed_data(
                invoice_id=invoice_id,
                status='processed', # This is the primary status update
                **parsed_data # Unpack all parsed fields as keyword arguments
            )

            if update_db_success:
                current_app.logger.info(f"Successfully processed and stored Textract Expense data for invoice ID {invoice_id}.")
                final_invoice_data = db_service.get_invoice_by_id(invoice_id)
                return jsonify({"message": "Textract Expense analysis processed and data stored.","invoice_id": invoice_id, "data": format_invoice_for_json(final_invoice_data)}), 200
            else:
                current_app.logger.error(f"Failed to update database with parsed expense data for invoice ID {invoice_id}.")
                return jsonify({"error": "Failed to update database with parsed Textract expense data."}), 500
        except Exception as e:
            current_app.logger.error(f"Error during parsing Textract Expense results or DB update for invoice {invoice_id}: {e}", exc_info=True)
            db_service.update_invoice_status(invoice_id, status='parsing_failed', error_message=f"Parsing/DB error: {str(e)[:200]}")
            return jsonify({"error": f"An error occurred while parsing Textract results: {str(e)}"}), 500
    elif actual_job_status_from_textract == 'FAILED':
        status_message = textract_response.get('StatusMessage', "Textract job failed."); warnings = textract_response.get('Warnings')
        if warnings: status_message += f" Warnings: {json.dumps(warnings)}"
        db_service.update_invoice_status(invoice_id, status='textract_failed', error_message=status_message[:250])
        return jsonify({"error": "Textract analysis failed.", "details": status_message}), 500
    elif actual_job_status_from_textract == 'IN_PROGRESS':
        if current_db_status != 'processing_textract': db_service.update_invoice_status(invoice_id, status='processing_textract')
        return jsonify({"message": "Textract analysis is still in progress.", "invoice_id": invoice_id, "job_status": actual_job_status_from_textract}), 202
    # ... other statuses
    else:
        db_service.update_invoice_status(invoice_id, status='textract_unknown_status', error_message=f"Unknown Textract status: {actual_job_status_from_textract}")
        return jsonify({"error": f"Unknown Textract job status: {actual_job_status_from_textract}"}), 500

# --- THIS IS THE ROUTE FOR THE INVOICES PAGE ---
@invoice_bp.route("/", methods=["GET"])
def get_invoices_route():
    db_service = current_app.extensions.get('db_service')
    if not db_service:
        current_app.logger.error("DbService not available in /invoices GET route.")
        return jsonify({"error": "Server configuration error, database service not available."}), 503
    try:
        limit = request.args.get('limit', 100, type=int) # Default to 100, can be overridden by query param
        offset = request.args.get('offset', 0, type=int)
        
        current_app.logger.info(f"GET /api/invoices/ - Calling db_service.get_all_invoices(limit={limit}, offset={offset})")
        invoices_raw = db_service.get_all_invoices(limit=limit, offset=offset)
        
        if invoices_raw is None: # Should return [] on error or no data, None is unexpected
            current_app.logger.error("db_service.get_all_invoices() returned None unexpectedly.")
            return jsonify({"error": "Database query failed to retrieve any invoices."}), 500
        
        current_app.logger.info(f"GET /api/invoices/ - Fetched {len(invoices_raw)} raw invoice(s) from DB.")
        if invoices_raw: # Log a sample only if data exists
             current_app.logger.debug(f"GET /api/invoices/ - First raw invoice sample: {invoices_raw[0]}")

        formatted_invoices = []
        if invoices_raw: # Only attempt to format if there are invoices
            for inv_raw in invoices_raw:
                formatted = format_invoice_for_json(inv_raw) # Use the helper
                if formatted: 
                    formatted_invoices.append(formatted)
                else:
                    current_app.logger.warning(f"GET /api/invoices/ - Invoice ID {inv_raw.get('id')} resulted in None after formatting. Raw: {inv_raw}")
        
        current_app.logger.info(f"GET /api/invoices/ - Returning {len(formatted_invoices)} formatted invoice(s).")
        if invoices_raw and len(formatted_invoices) < len(invoices_raw):
            current_app.logger.warning("GET /api/invoices/ - Some raw invoices were not formatted correctly and were excluded.")
        
        return jsonify(formatted_invoices), 200
    except Exception as e:
        current_app.logger.error(f"Error in get_invoices_route: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve invoices due to an internal server error"}), 500

@invoice_bp.route("/<int:invoice_id>", methods=["GET"])
def get_invoice_detail_route(invoice_id):
    # ... (This route was already correct, uses format_invoice_for_json) ...
    db_service = current_app.extensions.get('db_service')
    if not db_service: return jsonify({"error": "Server configuration error."}), 503
    try:
        invoice = db_service.get_invoice_by_id(invoice_id)
        if invoice: return jsonify(format_invoice_for_json(invoice)), 200
        else: return jsonify({"error": "Invoice not found"}), 404
    except Exception as e: current_app.logger.error(f"Error fetching invoice {invoice_id}: {e}", exc_info=True); return jsonify({"error": "Failed to retrieve details"}), 500

@invoice_bp.route("/<int:invoice_id>", methods=["PUT"])
def update_invoice_route(invoice_id):
    # ... (This route was already correct, uses format_invoice_for_json for response) ...
    db_service = current_app.extensions.get('db_service')
    if not db_service: return jsonify({"error": "Server configuration error."}), 503
    data = request.get_json();
    if not data: return jsonify({"error": "No JSON data provided"}), 400
    current_app.logger.info(f"Attempting to update invoice ID {invoice_id} with: {data}")
    allowed_fields = {'user_category': data.get('user_category')}
    update_payload = {k: v for k, v in allowed_fields.items() if v is not None or (k == 'user_category' and v == '')}
    if 'user_category' in update_payload and update_payload['user_category'] == '': update_payload['user_category'] = None
    if not update_payload: return jsonify({"error": "No valid fields"}), 400
    try:
        if not db_service.get_invoice_by_id(invoice_id): return jsonify({"error": "Invoice not found"}), 404
        success = db_service.update_invoice_fields(invoice_id, update_payload)
        if success:
            updated_invoice_dict = db_service.get_invoice_by_id(invoice_id)
            return jsonify({"message": f"Invoice ID {invoice_id} updated.","invoice": format_invoice_for_json(updated_invoice_dict)}), 200
        else: current_app.logger.error(f"Update op false for invoice {invoice_id}."); return jsonify({"error": "Failed to update in DB."}), 500
    except Exception as e: current_app.logger.error(f"Exception during update for invoice {invoice_id}: {e}", exc_info=True); return jsonify({"error": "Internal server error during update."}), 500

@invoice_bp.route("/<int:invoice_id>/view-url", methods=["GET"])
def get_invoice_view_url_route(invoice_id):
    # ... (This route is fine as is) ...
    db_service = current_app.extensions.get('db_service'); s3_service = current_app.extensions.get('s3_service')
    if not all([db_service, s3_service]): return jsonify({"error": "Server configuration error."}), 503
    invoice = db_service.get_invoice_by_id(invoice_id)
    if not invoice: return jsonify({"error": "Invoice not found"}), 404
    s3_key = invoice.get('s3_key'); s3_bucket_from_db = invoice.get('s3_bucket_name')
    if not s3_key or not s3_bucket_from_db: return jsonify({"error": "Invoice S3 details missing."}), 404
    presigned_url = s3_service.get_presigned_url(object_key=s3_key, bucket_name=s3_bucket_from_db)
    if presigned_url: return jsonify({"invoice_id": invoice_id, "view_url": presigned_url}), 200
    else: current_app.logger.error(f"Failed to generate presigned URL for invoice {invoice_id}"); return jsonify({"error": "Could not generate view URL."}), 500

@invoice_bp.route("/<int:invoice_id>", methods=["DELETE"]) # Added in previous step
def delete_invoice_route(invoice_id):
    db_service = current_app.extensions.get('db_service')
    s3_service = current_app.extensions.get('s3_service')
    if not db_service or not s3_service: return jsonify({"error": "Server configuration error."}), 503
    try:
        invoice = db_service.get_invoice_by_id(invoice_id)
        if not invoice: return jsonify({"error": "Invoice not found"}), 404
        s3_key_to_delete = invoice.get('s3_key')
        if s3_key_to_delete:
            s3_bucket = invoice.get('s3_bucket_name') or s3_service.bucket_name
            deleted_from_s3 = s3_service.delete_file_obj(s3_key_to_delete, bucket_name=s3_bucket)
            if deleted_from_s3: current_app.logger.info(f"S3 file deleted: {s3_bucket}/{s3_key_to_delete}")
            else: current_app.logger.error(f"Failed S3 delete: {s3_bucket}/{s3_key_to_delete}. Proceeding with DB delete.")
        deleted_from_db = db_service.delete_invoice_by_id(invoice_id)
        if deleted_from_db: return jsonify({"message": f"Invoice ID {invoice_id} deleted."}), 200
        else: current_app.logger.error(f"Invoice ID {invoice_id} found but DB delete failed."); return jsonify({"error": "Failed to delete from DB."}), 500
    except Exception as e: current_app.logger.error(f"Error deleting invoice {invoice_id}: {e}", exc_info=True); return jsonify({"error": "Internal error during delete."}), 500