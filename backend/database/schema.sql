-- InvoxAI Database Schema Setup
-- File: backend/sql/schema.sql

-- Drop existing database and user if they exist (for a clean setup during development)
-- Be CAREFUL with these in a production environment!
DROP DATABASE IF EXISTS invoxdb;
DROP USER IF EXISTS 'developer'@'localhost';

-- Create the database
CREATE DATABASE invoxdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create a dedicated user for the application
CREATE USER 'developer'@'localhost' IDENTIFIED BY 'developer';

-- Grant all privileges on the new database to the new user
GRANT ALL PRIVILEGES ON invoxdb.* TO 'developer'@'localhost';

-- Apply the privilege changes
FLUSH PRIVILEGES;

-- Switch to the invoxdb database
USE invoxdb;

-- Create the invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_category VARCHAR(100),
    s3_bucket_name VARCHAR(255),
    s3_key VARCHAR(1024),
    original_filename VARCHAR(255),
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending_upload',
    textract_job_id VARCHAR(255),
    vendor_name VARCHAR(255),
    invoice_id_number VARCHAR(100),
    invoice_date DATE,
    due_date DATE,
    total_amount DECIMAL(12, 2),
    currency VARCHAR(10),
    line_items JSON,
    parsed_data JSON,
    user_category VARCHAR(100),
    last_modified_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    error_message TEXT,
    UNIQUE KEY unique_s3_key (s3_key(255)),
    INDEX idx_invoices_vendor_name (vendor_name),
    INDEX idx_invoices_invoice_date (invoice_date),
    INDEX idx_invoices_status (status)
);


-- Create the chat_logs table
CREATE TABLE IF NOT EXISTS chat_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_message TEXT NOT NULL,
    assistant_response TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_chat_logs_session_id (session_id)
);