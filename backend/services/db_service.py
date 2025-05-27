# backend/services/db_service.py
import mysql.connector
from mysql.connector import Error # For catching specific MySQL errors
from flask import current_app, g # Flask's application context and request context globals
import json # For handling JSON data (line_items, parsed_data)
import logging # For application logging
from decimal import Decimal, InvalidOperation # For precise monetary values
from datetime import datetime, timedelta, date # For date manipulations

# Standard logger for this module
logger = logging.getLogger(__name__)

# --- Database Connection Management ---
# These functions handle the database connection per request using Flask's 'g' object.

def get_db_config():
    """Helper function to retrieve database configuration from the Flask app's config."""
    config = {
        'host': current_app.config['DB_HOST'],
        'port': current_app.config.get('DB_PORT', 3306), # Default MySQL port
        'database': current_app.config['DB_DATABASE'],
        'user': current_app.config['DB_USERNAME'],
        'password': current_app.config['DB_PASSWORD']
    }
    # Ensure port is an integer
    if not config['port']: 
        config['port'] = 3306
    else:
        try: 
            config['port'] = int(config['port'])
        except (ValueError, TypeError): # Catch errors if port is not a valid number
            logger.error(f"Invalid DB_PORT value: {config['port']}. Using default 3306.")
            config['port'] = 3306
    return config

def get_db():
    """
    Opens a new database connection if one doesn't exist for the current app context (request),
    or reuses an existing one for the current context.
    Stores the connection in Flask's 'g' object.
    """
    # Check if 'db_conn' is in 'g' and if the connection is still active
    if 'db_conn' not in g or not hasattr(g.db_conn, 'is_connected') or not g.db_conn.is_connected():
        try:
            config = get_db_config()
            logger.debug(f"Attempting to connect to DB: {config['host']}:{config['port']}/{config['database']} as user '{config['user']}'")
            g.db_conn = mysql.connector.connect(**config)
            logger.info(f"Successfully connected to MySQL database: {config.get('database')}")
        except Error as e:
            logger.error(f"Error connecting to MySQL Database: {e}", exc_info=True)
            g.db_conn = None # Ensure it's None if connection failed
            raise # Re-raise the exception to signal failure to the caller
    return g.db_conn

def close_db(e=None):
    """Closes the database connection at the end of the request (if it was opened)."""
    db_conn = g.pop('db_conn', None) # Get and remove connection from 'g'
    if db_conn is not None and hasattr(db_conn, 'is_connected') and db_conn.is_connected():
        try:
            db_conn.close()
            logger.info("MySQL database connection closed.")
        except Error as e:
            logger.error(f"Error closing MySQL connection: {e}", exc_info=True)

def init_app(app):
    """Registers database close function with the Flask app to be called after each request."""
    app.teardown_appcontext(close_db)

# --- DbService Class ---
class DbService:
    """
    Service class for all database interactions.
    It defines methods for CRUD operations, analytics queries, and report data fetching.
    """

    # Columns in the 'invoices' table that are populated from parsed Textract data
    INVOICE_TABLE_PARSED_COLUMNS = [
        'vendor_name', 'invoice_id_number', 'invoice_date', 'due_date', 
        'total_amount', 'subtotal', 'tax', 'currency', # Added subtotal, tax here for completeness if schema has them
        'line_items', 'parsed_data', # 'parsed_data' stores the full raw JSON from Textract service
        'user_category' 
    ]
    # Columns in 'invoices' table that are allowed to be updated via a generic PUT request (e.g., manual edits)
    INVOICE_TABLE_EDITABLE_COLUMNS = [
        'vendor_name', 'invoice_id_number', 'invoice_date', 'due_date', 
        'total_amount', 'subtotal', 'tax', 'currency', # Added subtotal, tax
        'user_category', 'status', 'error_message'
    ]

    def __init__(self, app_config):
        """
        Initializes the DbService.
        :param app_config: The Flask application's configuration object.
        """
        self.config = app_config
        if not self.config.get('DB_DATABASE'):
            logger.warning("DbService initialized but DB_DATABASE config is missing.")

    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False, is_insert=False):
        """
        A generic helper method to execute SQL queries.
        Manages cursor creation, execution, commit/rollback, and result fetching.
        :param query: The SQL query string.
        :param params: A tuple or list of parameters for the query.
        :param fetch_one: True if expecting a single row result.
        :param fetch_all: True if expecting multiple rows.
        :param is_insert: True if it's an INSERT query to get lastrowid.
        :return: Query result (single row, all rows, last insert ID, or row count) or None on error.
        """
        conn = None; cursor = None; result = None
        try:
            conn = get_db() # Gets a connection from the request context pool
            if conn is None: 
                logger.error("execute_query: Database connection not available.")
                raise Error("Database connection not available for query execution.")
            
            # Use dictionary cursor for SELECT queries for easier access to columns by name
            use_dictionary_cursor = (fetch_one or fetch_all) and not is_insert
            cursor = conn.cursor(dictionary=use_dictionary_cursor)
            
            logger.debug(f"Executing SQL query: {query} with params: {params}")
            cursor.execute(query, params)

            if is_insert:
                conn.commit() # Commit changes for INSERT, UPDATE, DELETE
                result = cursor.lastrowid # Get the ID of the newly inserted row
                logger.info(f"INSERT query successful. Last inserted ID: {result}")
            elif fetch_one:
                result = cursor.fetchone() # Fetch a single row
            elif fetch_all:
                result = cursor.fetchall() # Fetch all matching rows
            else: # For UPDATE, DELETE, or other non-SELECT, non-INSERT queries
                conn.commit()
                result = cursor.rowcount # Number of rows affected
                logger.info(f"Query executed successfully. Rows affected: {result}")
        except Error as e: # Catch MySQL specific errors
            logger.error(f"Database query error: {e}. Query: '{query}', Params: '{params}'", exc_info=True)
            if conn and conn.in_transaction: # Check if a transaction is active
                try:
                    conn.rollback()
                    logger.info("Database transaction rolled back due to error.")
                except Error as rb_e:
                    logger.error(f"Error during database transaction rollback: {rb_e}")
            raise # Re-raise the exception so the calling route can handle it (e.g., return 500)
        finally:
            if cursor:
                cursor.close()
            # Connection itself is closed by the teardown_appcontext hook (close_db)
        return result

    # --- Invoice CRUD & Update Methods ---
    def create_invoice_record(self, original_filename, s3_bucket=None, s3_key=None, status='pending_upload'):
        """Creates an initial record for an invoice when it's first uploaded."""
        sql = "INSERT INTO invoices (original_filename, s3_bucket_name, s3_key, status) VALUES (%s, %s, %s, %s)"
        try:
            invoice_id = self.execute_query(sql, (original_filename, s3_bucket, s3_key, status), is_insert=True)
            return self.get_invoice_by_id(invoice_id) if invoice_id else None
        except Error: return None # execute_query already logged the error

    def get_invoice_by_id(self, invoice_id):
        """Retrieves a single invoice by its primary ID."""
        sql = "SELECT * FROM invoices WHERE id = %s"
        try: return self.execute_query(sql, (invoice_id,), fetch_one=True)
        except Error: return None

    def get_all_invoices(self, limit=100, offset=0):
        """Retrieves a paginated list of all invoices, ordered by upload time."""
        sql = "SELECT * FROM invoices ORDER BY upload_timestamp DESC LIMIT %s OFFSET %s"
        try: return self.execute_query(sql, (limit, offset), fetch_all=True)
        except Error: return []

    def update_invoice_status(self, invoice_id, status, textract_job_id=None, error_message=None):
        """Updates the status, and optionally Textract job ID and error message, of an invoice."""
        sql_parts = ["UPDATE invoices SET status = %s"]; params = [status]
        if textract_job_id is not None: sql_parts.append("textract_job_id = %s"); params.append(textract_job_id)
        if error_message is not None: sql_parts.append("error_message = %s"); params.append(error_message)
        elif status not in ['error', 'textract_failed', 'parsing_failed', 'db_update_failed_post_textract', 's3_upload_failed', 'textract_submission_failed', 'textract_unknown_status']:
            # Clear error message if status is positive and no new error is provided
            sql_parts.append("error_message = NULL")
        sql = ", ".join(sql_parts) + " WHERE id = %s"; params.append(invoice_id)
        try: return self.execute_query(sql, tuple(params)) > 0 # Returns True if rows_affected > 0
        except Error: return False

    def update_invoice_s3_details(self, invoice_id, s3_bucket, s3_key, status):
        """Updates an invoice record with S3 bucket, key after successful upload, and sets a new status."""
        sql = "UPDATE invoices SET s3_bucket_name = %s, s3_key = %s, status = %s, error_message = NULL WHERE id = %s"
        try: return self.execute_query(sql, (s3_bucket, s3_key, status, invoice_id)) > 0
        except Error: return False
            
    def update_invoice_parsed_data(self, invoice_id, status='processed', **parsed_fields):
        """
        Updates an invoice with data extracted by Textract (from parse_expense_data).
        Only attempts to update columns defined in self.INVOICE_TABLE_PARSED_COLUMNS (plus status and error_message).
        The full raw output from TextractService's parser should be passed in parsed_fields['parsed_data_detail']
        and will be stored in the 'parsed_data' JSON column.
        """
        fields_to_update_sql = []
        params_sql = []

        for key, value in parsed_fields.items():
            if key in self.INVOICE_TABLE_PARSED_COLUMNS: # Check against schema-aware list
                fields_to_update_sql.append(f"`{key}` = %s")
                # Convert Python Decimal to string for SQL if DB driver or column type requires it.
                # MySQL connector handles Python Decimals well for DECIMAL columns.
                # For JSON columns (line_items, parsed_data), ensure Decimals are serializable.
                if key in ['total_amount', 'subtotal', 'tax'] and isinstance(value, Decimal):
                    params_sql.append(value) # Store as Decimal
                elif key in ['line_items'] and value is not None: # For line_items to be stored as JSON
                    params_sql.append(json.dumps(value, default=str)) # default=str handles Decimals in list
                else:
                    params_sql.append(value)
            elif key == 'parsed_data_detail': # This is the raw JSON from TextractService
                fields_to_update_sql.append("`parsed_data` = %s")
                params_sql.append(json.dumps(value, default=str)) # default=str for any Decimals within

        if not fields_to_update_sql and 'parsed_data_detail' not in parsed_fields: 
             logger.info(f"No specific schema fields from parser to update for invoice ID {invoice_id}, only status.")
        
        fields_to_update_sql.append("`status` = %s"); params_sql.append(status)
        fields_to_update_sql.append("`error_message` = NULL") # Clear any previous processing error
        
        sql = f"UPDATE invoices SET {', '.join(fields_to_update_sql)} WHERE id = %s"
        params_sql.append(invoice_id)

        try:
            logger.debug(f"Updating parsed data for invoice {invoice_id}. PARAMS (types before DB): {[(type(p), p) for p in params_sql]}")
            return self.execute_query(sql, tuple(params_sql)) > 0
        except Error as e: 
            try: self.update_invoice_status(invoice_id, status='db_update_failed_post_textract', error_message=f"DB update error: {str(e)[:200]}")
            except: pass # Avoid error in error handling
            return False

    def update_invoice_fields(self, invoice_id, fields_to_update): # For general manual edits like category
        """Updates specified fields for a given invoice_id based on INVOICE_TABLE_EDITABLE_COLUMNS."""
        if not fields_to_update: return False
        set_clauses = []; params = []
        for key, value in fields_to_update.items():
            if key in self.INVOICE_TABLE_EDITABLE_COLUMNS:
                set_clauses.append(f"`{key}` = %s")
                if key in ['total_amount', 'subtotal', 'tax'] and value is not None: # Handle potential string input for amounts
                    try: params.append(Decimal(str(value))) 
                    except InvalidOperation: logger.error(f"Invalid amount value '{value}' for field '{key}' in update_invoice_fields."); return False 
                else: params.append(value) # Other fields (dates, strings) as is
            else: logger.warning(f"Attempted to update disallowed field '{key}' via update_invoice_fields.")
        if not set_clauses: return False
        sql = f"UPDATE invoices SET {', '.join(set_clauses)} WHERE id = %s"; params.append(invoice_id)
        try: 
            logger.debug(f"Updating invoice fields for ID {invoice_id} with SQL: {sql} and PARAMS: {params}")
            return self.execute_query(sql, tuple(params)) > 0
        except Error: return False # Error logged by execute_query

    # --- Analytics Methods ---
    def get_analytics_summary(self): # ... (no changes from last full version)
        sql_total_spent = "SELECT SUM(total_amount) as total_spent FROM invoices WHERE status = 'processed'"
        sql_invoice_count = "SELECT COUNT(*) as total_invoices FROM invoices WHERE status = 'processed'"
        total_spent_result = 0.0; invoice_count_result = 0
        try:
            spent_data = self.execute_query(sql_total_spent, fetch_one=True)
            if spent_data and spent_data.get('total_spent') is not None: total_spent_result = float(spent_data['total_spent'])
            count_data = self.execute_query(sql_invoice_count, fetch_one=True)
            if count_data and count_data.get('total_invoices') is not None: invoice_count_result = int(count_data['total_invoices'])
            return {"total_spent": total_spent_result, "total_invoices": invoice_count_result}
        except Error: return {"total_spent": 0.0, "total_invoices": 0}
    def get_expenses_by_vendor(self, limit=None): # ... (no changes from last full version)
        sql = "SELECT vendor_name, SUM(total_amount) as tsfv, COUNT(*) as invoice_count FROM invoices WHERE status = 'processed' AND vendor_name IS NOT NULL AND vendor_name != 'N/A' AND vendor_name != '' GROUP BY vendor_name ORDER BY tsfv DESC"
        params = []
        if limit is not None: sql += " LIMIT %s"; params.append(limit)
        try: results = self.execute_query(sql, tuple(params) if params else None, fetch_all=True); return [{**row, 'total_spent_for_vendor': float(row.pop('tsfv'))} for row in results] if results else []
        except Error: return []
    def get_expenses_by_category(self, limit=None): # ... (no changes from last full version)
        sql = "SELECT user_category, SUM(total_amount) as tsfc, COUNT(*) as invoice_count FROM invoices WHERE status = 'processed' AND user_category IS NOT NULL AND user_category != '' GROUP BY user_category ORDER BY tsfc DESC"
        params = [];
        if limit is not None: sql += " LIMIT %s"; params.append(limit)
        try: results = self.execute_query(sql, tuple(params) if params else None, fetch_all=True); return [{**row, 'total_spent_for_category': float(row.pop('tsfc'))} for row in results] if results else []
        except Error: return []
    def get_monthly_spend(self): # ... (no changes from last full version)
        sql = "SELECT DATE_FORMAT(invoice_date, '%Y-%m') as month_year, SUM(total_amount) as monthly_total, COUNT(*) as invoice_count FROM invoices WHERE status = 'processed' AND invoice_date IS NOT NULL GROUP BY month_year ORDER BY month_year ASC"
        try: results = self.execute_query(sql, fetch_all=True); return [{**row, 'monthly_total': float(row['monthly_total'])} for row in results] if results else []
        except Error: return []
    def get_invoices_by_filter(self, filters, limit=5, offset=0): # ... (no changes from last full version)
        if not isinstance(filters, dict): logger.error("get_invoices_by_filter: filters must be a dict."); return []
        where_clauses = []; params = [] 
        has_specific_status_filter = False
        if filters.get('status_exact_match'): where_clauses.append("`status` = %s"); params.append(filters['status_exact_match']); has_specific_status_filter = True
        elif filters.get('status_like_match'): where_clauses.append("`status` LIKE %s"); params.append(filters['status_like_match']); has_specific_status_filter = True
        if not has_specific_status_filter: where_clauses.append("`status` = 'processed'")
        if filters.get('id_exact_match') and isinstance(filters.get('id_exact_match'), int): where_clauses.append("`id` = %s"); params.append(filters['id_exact_match'])
        if filters.get('vendor_name_like'): where_clauses.append("`vendor_name` LIKE %s"); params.append(f"%{filters['vendor_name_like']}%")
        if filters.get('user_category_like'): where_clauses.append("`user_category` LIKE %s"); params.append(f"%{filters['user_category_like']}%")
        if filters.get('invoice_date_exact'): where_clauses.append("`invoice_date` = %s"); params.append(filters['invoice_date_exact'])
        else: 
            if filters.get('invoice_date_start'): where_clauses.append("`invoice_date` >= %s"); params.append(filters['invoice_date_start'])
            if filters.get('invoice_date_end'): where_clauses.append("`invoice_date` <= %s"); params.append(filters['invoice_date_end'])
        if filters.get('total_amount_gt') is not None: where_clauses.append("`total_amount` > %s"); params.append(Decimal(str(filters['total_amount_gt'])))
        if filters.get('total_amount_lt') is not None: where_clauses.append("`total_amount` < %s"); params.append(Decimal(str(filters['total_amount_lt'])))
        base_sql = "SELECT id, original_filename, vendor_name, invoice_date, total_amount, currency, user_category, status FROM invoices" # Select specific fields
        if where_clauses: base_sql += " WHERE " + " AND ".join(where_clauses)
        order_by_clause = filters.get('order_by', 'invoice_date DESC, id DESC') 
        allowed_sort_cols = ['upload_timestamp', 'invoice_date', 'total_amount', 'vendor_name', 'status', 'id']
        sort_col_candidate = order_by_clause.split(' ')[0].lower(); sort_dir_candidate = order_by_clause.split(' ')[-1].upper() if len(order_by_clause.split(' ')) > 1 else 'DESC'
        if sort_col_candidate not in allowed_sort_cols or sort_dir_candidate not in ['ASC', 'DESC']: order_by_clause = 'invoice_date DESC, id DESC'
        base_sql += f" ORDER BY {order_by_clause}"
        base_sql += " LIMIT %s OFFSET %s"; params.extend([limit, offset])
        try:
            logger.debug(f"Executing get_invoices_by_filter query: {base_sql} with params: {params}")
            results = self.execute_query(base_sql, tuple(params), fetch_all=True)
            if results:
                for row in results: # Convert Decimal to float for easier JSON handling if needed
                    if row.get('total_amount') is not None and isinstance(row['total_amount'], Decimal): row['total_amount'] = float(row['total_amount']) 
                    if row.get('invoice_date') is not None and isinstance(row['invoice_date'], date): row['invoice_date'] = row['invoice_date'].isoformat()
            return results if results else []
        except Error: return []

    # --- Methods for Comprehensive Report Data ---
    def get_comprehensive_report_summary_stats(self, year=None, month=None, vendor_name=None, category=None): # ... (no changes from last full version)
        where_clauses = ["`status` = 'processed'"]; params = []
        if year and month:
            try: start_date_obj = datetime(year, month, 1); end_date_obj = (start_date_obj.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            except ValueError: logger.error(f"Invalid year/month for report summary: {year}-{month}"); return None
            where_clauses.append("`invoice_date` BETWEEN %s AND %s"); params.extend([start_date_obj.strftime('%Y-%m-%d'), end_date_obj.strftime('%Y-%m-%d')])
        elif year: where_clauses.append("`invoice_date` BETWEEN %s AND %s"); params.extend([f"{year}-01-01", f"{year}-12-31"])
        if vendor_name: where_clauses.append("`vendor_name` LIKE %s"); params.append(f"%{vendor_name}%")
        if category: where_clauses.append("`user_category` LIKE %s"); params.append(f"%{category}%")
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        sql_summary = f"SELECT COUNT(*) as `total_invoices`, SUM(`total_amount`) as `total_spent`, MIN(`invoice_date`) as `oldest_invoice_date`, MAX(`invoice_date`) as `newest_invoice_date`, COUNT(DISTINCT `vendor_name`) as `unique_vendors` FROM invoices WHERE {where_sql}"
        try:
            logger.debug(f"Executing get_comprehensive_report_summary_stats: {sql_summary} with {params}")
            summary_data = self.execute_query(sql_summary, tuple(params) if params else None, fetch_one=True)
            if summary_data:
                total_spent = summary_data.get('total_spent'); oldest_date_val = summary_data.get('oldest_invoice_date'); newest_date_val = summary_data.get('newest_invoice_date')
                return {"total_invoices": int(summary_data.get('total_invoices',0) or 0),"total_spent": float(total_spent) if total_spent else 0.0,"oldest_invoice_date": oldest_date_val.isoformat() if isinstance(oldest_date_val, date) else None,"newest_invoice_date": newest_date_val.isoformat() if isinstance(newest_date_val, date) else None,"unique_vendors": int(summary_data.get('unique_vendors',0) or 0)}
            return {"total_invoices":0, "total_spent":0.0, "oldest_invoice_date":None, "newest_invoice_date":None, "unique_vendors":0}
        except Error as e: logger.error(f"Error fetching comprehensive summary stats: {e}", exc_info=True); return None
    def get_invoice_status_counts(self): # ... (no changes from last full version)
        sql = "SELECT `status`, COUNT(*) as count FROM invoices GROUP BY `status`"
        try: results = self.execute_query(sql, fetch_all=True); return {row['status']: int(row['count']) for row in results} if results else {}
        except Error as e: logger.error(f"Error fetching status counts: {e}", exc_info=True); return {}
    def get_invoices_for_report(self, year, month, vendor_name=None, category=None, limit_for_details=15): # ... (no changes from last full version)
        try: start_date = datetime(year, month, 1); end_date = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        except ValueError: logger.error(f"Invalid year/month for get_invoices_for_report: {year}-{month}."); return []
        filters = {"invoice_date_start": start_date.strftime('%Y-%m-%d'),"invoice_date_end": end_date.strftime('%Y-%m-%d'),"status_exact_match": "processed" }
        if vendor_name: filters["vendor_name_like"] = vendor_name
        if category: filters["user_category_like"] = category
        select_fields = "id, original_filename, vendor_name, invoice_date, due_date, total_amount, currency, user_category, line_items, status, s3_key"
        where_clauses = ["`status` = %s", "`invoice_date` >= %s", "`invoice_date` <= %s"]; params = [filters["status_exact_match"], filters["invoice_date_start"], filters["invoice_date_end"]]
        if filters.get('vendor_name_like'): where_clauses.append("`vendor_name` LIKE %s"); params.append(f"%{filters['vendor_name_like']}%")
        if filters.get('user_category_like'): where_clauses.append("`user_category` LIKE %s"); params.append(f"%{filters['user_category_like']}%")
        sql = f"SELECT {select_fields} FROM invoices WHERE {' AND '.join(where_clauses)} ORDER BY invoice_date ASC, id ASC LIMIT %s"; params.append(limit_for_details)
        try:
            logger.debug(f"Executing get_invoices_for_report query: {sql} with params: {params}")
            invoices = self.execute_query(sql, tuple(params), fetch_all=True)
            if invoices:
                for inv in invoices: 
                    if inv.get('total_amount') is not None and isinstance(inv['total_amount'], Decimal): inv['total_amount'] = float(inv['total_amount'])
                    if inv.get('invoice_date') and isinstance(inv['invoice_date'], date): inv['invoice_date'] = inv['invoice_date'].isoformat()
                    if inv.get('due_date') and isinstance(inv['due_date'], date): inv['due_date'] = inv['due_date'].isoformat()
                    if inv.get('line_items') and isinstance(inv['line_items'], str): 
                        try: 
                            line_items_data = json.loads(inv['line_items'])
                            if isinstance(line_items_data, list):
                                for item in line_items_data:
                                    if isinstance(item, dict):
                                        for k_li, v_li in item.items():
                                            if isinstance(v_li, Decimal): item[k_li] = float(v_li)
                            inv['line_items'] = line_items_data
                        except: inv['line_items'] = [] 
            return invoices if invoices else []
        except Error as e: logger.error(f"Error fetching invoices for report data: {e}", exc_info=True); return []

    def delete_invoice_by_id(self, invoice_id): 
        sql = "DELETE FROM invoices WHERE id = %s"
        try:
            rows_affected = self.execute_query(sql, (invoice_id,))
            if rows_affected > 0: logger.info(f"Successfully deleted invoice ID {invoice_id} from database."); return True
            else: logger.warning(f"No invoice found with ID {invoice_id} to delete."); return False
        except Error: return False