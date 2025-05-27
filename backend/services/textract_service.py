# backend/services/textract_service.py
import boto3
from botocore.exceptions import ClientError
import json
from dateutil import parser as date_parser
import logging
from decimal import Decimal, InvalidOperation 
import re

logger = logging.getLogger(__name__)

class TextractService:
    def __init__(self, app_config):
        self.config = app_config
        self.aws_access_key_id = self.config.get('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = self.config.get('AWS_SECRET_ACCESS_KEY')
        self.region_name = self.config.get('AWS_REGION')
        self.s3_bucket_name = self.config.get('S3_BUCKET_NAME')

        if not self.region_name:
            logger.error("TextractService: AWS_REGION not configured.")
            raise ValueError("TextractService: AWS_REGION not configured.")
        if not self.s3_bucket_name:
            logger.error("TextractService: S3_BUCKET_NAME not configured.")
            raise ValueError("TextractService: S3_BUCKET_NAME not configured for Textract document location.")

        if self.aws_access_key_id and self.aws_secret_access_key:
            self.textract_client = boto3.client(
                'textract',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name
            )
            logger.info("TextractService initialized with explicit credentials (for AnalyzeExpense).")
        else:
            self.textract_client = boto3.client('textract', region_name=self.region_name)
            logger.info("TextractService initialized (credentials will be sourced by boto3 for AnalyzeExpense).")

    def start_expense_analysis(self, s3_object_key, client_request_token=None, job_tag=None):
        try:
            params = {
                'DocumentLocation': {
                    'S3Object': {
                        'Bucket': self.s3_bucket_name,
                        'Name': s3_object_key
                    }
                }
            }
            if client_request_token: params['ClientRequestToken'] = client_request_token
            if job_tag: params['JobTag'] = job_tag
            response = self.textract_client.start_expense_analysis(**params)
            job_id = response.get('JobId')
            logger.info(f"Started Textract Expense Analysis for S3 key {s3_object_key}. JobId: {job_id}")
            return job_id
        except ClientError as e:
            logger.error(f"Textract ClientError starting expense analysis for {s3_object_key}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error starting Textract expense analysis: {e}", exc_info=True)
            return None

    def get_expense_analysis_results_page(self, job_id, max_results=100, next_token=None):
        try:
            params = {'JobId': job_id, 'MaxResults': max_results}
            if next_token: params['NextToken'] = next_token
            response = self.textract_client.get_expense_analysis(**params)
            return response
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == 'InvalidJobIdException':
                logger.warn(f"Textract GetExpenseAnalysis: Invalid JobId {job_id}.")
            else:
                logger.error(f"Textract ClientError getting expense results for JobId {job_id}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting Textract expense results for JobId {job_id}: {e}", exc_info=True)
            return None

    def get_all_expense_results_paginated(self, job_id):
        all_expense_documents = []
        document_metadata = None
        job_status = 'NOT_FETCHED_YET'
        next_token = None
        model_version = None
        warnings_list = []
        MAX_PAGES_TO_FETCH = 10 
        pages_fetched = 0
        while pages_fetched < MAX_PAGES_TO_FETCH:
            pages_fetched += 1
            logger.debug(f"Fetching page {pages_fetched} for Textract Expense JobId: {job_id}, NextToken: {next_token}")
            response = self.get_expense_analysis_results_page(job_id, next_token=next_token)
            if not response:
                logger.error(f"Failed to fetch expense results for page {pages_fetched}, JobId: {job_id}. Previous status: {job_status}")
                return {'JobStatus': 'FAILED_TO_FETCH_RESULTS', 'ExpenseDocuments': [], 'DocumentMetadata': None, 'Warnings': warnings_list}
            current_job_status_on_page = response.get('JobStatus')
            if job_status == 'NOT_FETCHED_YET' or job_status == 'IN_PROGRESS':
                 job_status = current_job_status_on_page
            if 'ExpenseDocuments' in response: all_expense_documents.extend(response['ExpenseDocuments'])
            if not document_metadata and 'DocumentMetadata' in response: document_metadata = response['DocumentMetadata']
            if not model_version and 'AnalyzeExpenseModelVersion' in response: model_version = response['AnalyzeExpenseModelVersion']
            if 'Warnings' in response: warnings_list.extend(response['Warnings'])
            next_token_from_response = response.get('NextToken')
            if not next_token_from_response:
                logger.debug(f"No NextToken. All pages fetched for Expense JobId {job_id}. Final JobStatus on page: {current_job_status_on_page}")
                break
            next_token = next_token_from_response
            if current_job_status_on_page != 'IN_PROGRESS' and not next_token:
                 logger.debug(f"Job status is '{current_job_status_on_page}' and no more pages. Breaking.")
                 break
        if pages_fetched >= MAX_PAGES_TO_FETCH and next_token:
            logger.warning(f"Reached MAX_PAGES_TO_FETCH ({MAX_PAGES_TO_FETCH}) for Expense JobId: {job_id}. Results might be incomplete.")
            warnings_list.append({"ErrorCode": "INCOMPLETE_RESULTS_MAX_PAGES", "Pages": str(pages_fetched)})
        logger.info(f"Finished fetching all pages for Expense JobId {job_id}. Final determined JobStatus: {job_status}. Total ExpenseDocuments: {len(all_expense_documents)}")
        return {
            'JobStatus': job_status,
            'ExpenseDocuments': all_expense_documents,
            'DocumentMetadata': document_metadata,
            'AnalyzeExpenseModelVersion': model_version,
            'Warnings': warnings_list
        }

    def _parse_decimal_from_textract_value(self, value_text, field_name_for_log="amount"):
        if not value_text: return None
        try:
            cleaned_val = value_text.replace('$', '').replace('£', '').replace('€', '').strip()
            if ',' in cleaned_val and '.' in cleaned_val:
                if cleaned_val.rfind(',') > cleaned_val.rfind('.'): 
                    cleaned_val = cleaned_val.replace('.', '').replace(',', '.')
                else: 
                    cleaned_val = cleaned_val.replace(',', '')
            elif ',' in cleaned_val:
                if cleaned_val.count(',') == 1 and len(cleaned_val.split(',')[-1]) != 3 :
                     cleaned_val = cleaned_val.replace(',', '.')
                else: 
                     cleaned_val = cleaned_val.replace(',', '')
            if cleaned_val.startswith('(') and cleaned_val.endswith(')'):
                cleaned_val = '-' + cleaned_val[1:-1]
            cleaned_val = re.sub(r'[^\d\.\-]', '', cleaned_val)
            if cleaned_val.count('.') > 1:
                first_dot_index = cleaned_val.find('.')
                cleaned_val = cleaned_val[:first_dot_index+1] + cleaned_val[first_dot_index+1:].replace('.', '')
            if cleaned_val and cleaned_val != '-' and cleaned_val != '.': return Decimal(cleaned_val)
        except InvalidOperation: logger.warning(f"[PARSER_DECIMAL_ERROR] Could not parse {field_name_for_log} from '{value_text}' (cleaned: '{cleaned_val}') to Decimal due to InvalidOperation.")
        except Exception as e: logger.warning(f"[PARSER_DECIMAL_ERROR] Unexpected error parsing {field_name_for_log} from '{value_text}' (cleaned: '{cleaned_val}'): {e}")
        return None

    def parse_expense_data(self, expense_documents):
        logger.info(f"Attempting to parse {len(expense_documents)} ExpenseDocument(s) using AnalyzeExpense structure.")
        if not expense_documents or len(expense_documents) == 0:
            logger.warning("No ExpenseDocuments received to parse.")
            return {} 

        doc = expense_documents[0] 
        
        extracted_data = {
            "vendor_name": None, "invoice_id_number": None, "invoice_date": None,
            "due_date": None, "total_amount": None, "subtotal": None, "tax": None,
            "currency": None, "line_items": [],
            "parsed_data_detail": {"summary_fields_detected": {}, "errors": []}
        }

        summary_fields_raw = {}
        summary_fields_upper_normalized = {} 

        for field in doc.get('SummaryFields', []):
            field_type_obj = field.get('Type', {})
            field_value_obj = field.get('ValueDetection', {})
            field_type_text = field_type_obj.get('Text')    
            field_value_text = field_value_obj.get('Text')
            
            if field_type_text and field_value_text:
                summary_fields_raw[field_type_text] = field_value_text
                normalized_key = re.sub(r'[\s\.:\(\)#]', '_', field_type_text.upper()).replace('__', '_').strip('_')
                summary_fields_upper_normalized[normalized_key] = field_value_text
                logger.debug(f"Raw SummaryField: Type='{field_type_text}' -> NormalizedKey='{normalized_key}', Value='{field_value_text}'")
        
        extracted_data["parsed_data_detail"]["summary_fields_detected"] = summary_fields_raw
        logger.debug(f"Normalized Summary Fields Upper for lookup: {summary_fields_upper_normalized}")
        
        # --- Map Summary Fields using summary_fields_upper_normalized ---
        extracted_data["vendor_name"] = summary_fields_upper_normalized.get('VENDOR_NAME') or \
                                        summary_fields_upper_normalized.get('VENDOR') or \
                                        summary_fields_upper_normalized.get('SUPPLIER_NAME') or \
                                        summary_fields_upper_normalized.get('MERCHANT_NAME')
        if not extracted_data["vendor_name"]:
            if summary_fields_upper_normalized.get("ISSUED_BY_SIGNATURE"):
                 extracted_data["vendor_name"] = summary_fields_upper_normalized.get("ISSUED_BY_SIGNATURE")
        logger.debug(f"Intermediate Vendor Name: {extracted_data['vendor_name']}")


        inv_num_keys = ['INVOICE_NO', 'REFERENCE', 'INVOICE_RECEIPT_ID', 'RECEIPT_NUMBER', 'INVOICE_ID', 'DOCUMENT_NUMBER', 'INV_NO']
        extracted_data["invoice_id_number"] = next((summary_fields_upper_normalized.get(key) for key in inv_num_keys if summary_fields_upper_normalized.get(key)), None)
        logger.debug(f"Invoice Number mapped to: {extracted_data['invoice_id_number']}")

        inv_date_keys = ['INVOICE_RECEIPT_DATE', 'ISSUE_DATE', 'EXPENSE_DATE', 'DATE', 'TRANSACTION_DATE', 'INVOICE_DATE']
        raw_date_str = next((summary_fields_upper_normalized.get(key) for key in inv_date_keys if summary_fields_upper_normalized.get(key)), None)
        if raw_date_str:
            try: 
                parsed_dt = date_parser.parse(raw_date_str, dayfirst=True if '/' in raw_date_str else False)
                extracted_data["invoice_date"] = parsed_dt.strftime('%Y-%m-%d')
                logger.debug(f"[DATE_PARSER_SUCCESS] Parsed Invoice Date: {extracted_data['invoice_date']} from raw '{raw_date_str}'")
            except Exception as e: 
                logger.warning(f"[DATE_PARSER_ERROR] For invoice_date from '{raw_date_str}': {e}")
                extracted_data["parsed_data_detail"]["errors"].append(f"Date parsing error for invoice date: {raw_date_str}")
                extracted_data["invoice_date"] = None # Ensure it's None if parsing fails
        else:
            logger.debug("No candidate found for Invoice Date in summary fields.")


        raw_due_date_str = summary_fields_upper_normalized.get('DUE_DATE') or summary_fields_upper_normalized.get('PAYMENT_DUE_DATE')
        if raw_due_date_str:
            try: 
                parsed_dt = date_parser.parse(raw_due_date_str, dayfirst=True if '/' in raw_due_date_str else False)
                extracted_data["due_date"] = parsed_dt.strftime('%Y-%m-%d')
                logger.debug(f"[DATE_PARSER_SUCCESS] Parsed Due Date: {extracted_data['due_date']} from raw '{raw_due_date_str}'")
            except Exception as e: 
                logger.warning(f"[DATE_PARSER_ERROR] For due_date from '{raw_due_date_str}': {e}")
                extracted_data["parsed_data_detail"]["errors"].append(f"Date parsing error for due date: {raw_due_date_str}")
                extracted_data["due_date"] = None # Ensure it's None if parsing fails
        else:
            logger.debug("No candidate found for Due Date in summary fields.")

        total_keys_normalized = ['TOTAL_GBP', 'TOTAL_DUE_GBP', 'AMOUNT_£', 'TOTAL', 'AMOUNT_DUE', 'BALANCE_DUE', 'GRAND_TOTAL', 'NET_AMOUNT']
        raw_total_str = next((summary_fields_upper_normalized.get(key) for key in total_keys_normalized if summary_fields_upper_normalized.get(key)), None)
        if raw_total_str:
            extracted_data["total_amount"] = self._parse_decimal_from_textract_value(raw_total_str, "TOTAL")
            logger.debug(f"Parsed Total Amount: {extracted_data['total_amount']} from raw string '{raw_total_str}'")
            if not extracted_data["currency"]:
                matched_key_original_case = next((k_raw for k_raw, v_raw in summary_fields_raw.items() if v_raw == raw_total_str), None)
                text_to_check_currency = (str(matched_key_original_case or '') + raw_total_str).lower() # Ensure string concatenation
                if "gbp" in text_to_check_currency or "£" in text_to_check_currency: extracted_data["currency"] = "GBP"
                elif "usd" in text_to_check_currency or "$" in text_to_check_currency: extracted_data["currency"] = "USD"
                elif "eur" in text_to_check_currency or "€" in text_to_check_currency: extracted_data["currency"] = "EUR"
                logger.debug(f"Inferred Currency based on total string: {extracted_data['currency']}")
        
        subtotal_str = summary_fields_upper_normalized.get('SUBTOTAL') or summary_fields_upper_normalized.get('SUB_TOTAL')
        if subtotal_str: extracted_data["subtotal"] = self._parse_decimal_from_textract_value(subtotal_str, "SUBTOTAL")
        
        tax_str = summary_fields_upper_normalized.get('TAX') or summary_fields_upper_normalized.get('TOTAL_TAX_AMOUNT') or \
                  summary_fields_upper_normalized.get('VAT') or summary_fields_upper_normalized.get('GST')
        if tax_str: extracted_data["tax"] = self._parse_decimal_from_textract_value(tax_str, "TAX")

        if not extracted_data["currency"]:
            explicit_currency_str = summary_fields_upper_normalized.get('CURRENCY') or summary_fields_upper_normalized.get('CURRENCY_CODE')
            if explicit_currency_str: extracted_data["currency"] = explicit_currency_str.strip().upper()
            logger.debug(f"Currency from explicit field: {extracted_data['currency']}")
        
        parsed_line_items = []
        for group_idx, group in enumerate(doc.get('LineItemGroups', [])):
            logger.debug(f"Processing LineItemGroupIndex: {group.get('LineItemGroupIndex', group_idx)}")
            for item_idx, line_item_obj in enumerate(group.get('LineItems', [])):
                current_item_parsed = {"description": None, "quantity": None, "unit_price": None, "amount": None, "product_code": None, "raw_fields": []}
                for field in line_item_obj.get('LineItemExpenseFields', []):
                    item_field_type_obj = field.get('Type', {})
                    item_field_value_obj = field.get('ValueDetection', {})
                    item_field_type_text = item_field_type_obj.get('Text')
                    item_field_value_text = item_field_value_obj.get('Text')
                    if item_field_type_text and item_field_value_text:
                        current_item_parsed["raw_fields"].append({"type": item_field_type_text, "value": item_field_value_text, "confidence": item_field_value_obj.get('Confidence')})
                        item_field_type_upper = item_field_type_text.upper().replace(' ', '_') 
                        if item_field_type_upper in ['ITEM', 'DESCRIPTION', 'SERVICE', 'PRODUCT_NAME']:
                            current_item_parsed['description'] = (current_item_parsed.get('description', '') + " " + item_field_value_text).strip() if current_item_parsed.get('description') else item_field_value_text
                        elif item_field_type_upper in ['PRODUCT_CODE', 'SKU', 'ITEM_CODE']:
                            current_item_parsed['product_code'] = item_field_value_text
                        elif item_field_type_upper == 'PRICE': 
                            current_item_parsed['amount'] = self._parse_decimal_from_textract_value(item_field_value_text, "Line Item PRICE")
                        elif item_field_type_upper in ['QUANTITY', 'QTY', 'UNITS']:
                            current_item_parsed['quantity'] = self._parse_decimal_from_textract_value(item_field_value_text, "Line Item QTY")
                        elif item_field_type_upper == 'UNIT_PRICE':
                            current_item_parsed['unit_price'] = self._parse_decimal_from_textract_value(item_field_value_text, "Line Item UNIT_PRICE")
                if current_item_parsed.get('description') or current_item_parsed.get('amount') is not None or current_item_parsed.get('quantity') is not None:
                    parsed_line_items.append(current_item_parsed)
                elif current_item_parsed["raw_fields"]: 
                    logger.debug(f"Line item {item_idx} in group {group_idx} had only raw fields: {current_item_parsed['raw_fields']}")
        extracted_data["line_items"] = parsed_line_items
        extracted_data["parsed_data_detail"]["line_item_groups_raw_count"] = len(doc.get('LineItemGroups', []))
        logger.info(
            f"Refined Parsed from AnalyzeExpense: Vendor='{extracted_data['vendor_name']}', "
            f"Date='{extracted_data['invoice_date']}', Total='{extracted_data['total_amount']}', "
            f"Inv#='{extracted_data['invoice_id_number']}', Currency='{extracted_data['currency']}', Items='{len(extracted_data['line_items'])}'"
        )
        logger.debug(f"Full Refined parsed expense data object: {json.dumps(extracted_data, default=str, indent=2)}") 
        return extracted_data