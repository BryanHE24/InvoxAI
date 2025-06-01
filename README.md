# InvoxAI - AI-Powered Invoice Intelligence System 

> Transform your invoice processing with intelligent automation and AI-driven insights

InvoxAI is a sophisticated full-stack web application that revolutionizes invoice management through advanced AI integration. Built with modern technologies, it provides automated invoice parsing, intelligent financial analytics, and conversational AI assistance for comprehensive financial data management.

## Overview

InvoxAI addresses the common business challenge of manual invoice processing by leveraging cutting-edge AI services. The system automatically extracts data from uploaded invoices, provides intelligent categorization suggestions, generates comprehensive financial insights, and offers a natural language interface for querying financial data.

**Perfect for:** Small to medium businesses, accounting firms, financial analysts, and anyone looking to modernize their invoice processing workflow.

## Core Features

### Intelligent Invoice Processing
- **Multi-format Support**: Upload PDF, JPG, and PNG invoice files
- **Secure Cloud Storage**: Documents stored safely in AWS S3
- **AI-Powered OCR**: AWS Textract's `AnalyzeExpense` API extracts:
  - Vendor information and contact details
  - Invoice numbers and reference codes
  - Dates (invoice, due, service periods)
  - Total amounts and currency detection
  - Detailed line items with descriptions and amounts
  - Tax information and payment terms

### Comprehensive Invoice Management
- **Smart Invoice Dashboard**: View all invoices with sortable columns and quick actions
- **Detailed Invoice Views**: Complete breakdown of extracted data with original document preview
- **Category Management**: Manual categorization with AI-suggested categories (future enhancement)
- **Status Tracking**: Real-time processing status from upload to completion
- **Bulk Operations**: Process multiple invoices efficiently

### Advanced Analytics & Insights
- **Executive KPI Dashboard**:
  - Total processed invoices and spend
  - Average invoice amounts and processing times
  - Month-over-month growth metrics
- **Interactive Visualizations** (Chart.js):
  - Top vendors by spend (Bar chart)
  - Expense categories breakdown (Pie chart)
  - Monthly spending trends (Line chart)
  - Quarterly comparisons and forecasting
- **AI-Generated Financial Insights**: OpenAI-powered analysis of spending patterns and trends

### Conversational AI Assistant
- **Natural Language Queries**: Ask questions like:
  - "What was my total spend with Dell last quarter?"
  - "Show me all invoices over $1,000 from this month"
  - "Which vendor do I spend the most with?"
- **Intelligent Context Understanding**: Advanced NLU pipeline that:
  - Extracts intent and entities from user queries
  - Queries relevant database context
  - Generates human-like responses with actual data
- **Floating Chat Interface**: Accessible across all application pages

### Professional Report Generation
- **Monthly Expense Reports**: Detailed Markdown reports with:
  - Executive summary and key metrics
  - Vendor breakdown and category analysis
  - Notable trends and anomalies
  - Filtering by vendor, category, and date range
- **Comprehensive Overview Reports**: All-time financial summaries


### Modern User Experience
- **"Invo." Inspired Design**: Clean, professional interface with:
  - Fixed sidebar navigation
  - Card-based information display
  - Consistent blue accent theme
  - Responsive layout for all devices
- **Intuitive Workflows**: Streamlined user journey from upload to insights
- **Real-time Updates**: Live status updates and progress indicators

## Architecture & Technology Stack

### Frontend Technologies
```
React 18+ (Vite)          - Modern React framework with fast HMR
React Router DOM          - Client-side routing and navigation
Axios                     - HTTP client for API communication
Chart.js + React wrapper  - Interactive data visualizations
React Markdown + GFM      - Markdown rendering with GitHub flavors
Custom CSS3               - Professional styling system
```

### Backend Technologies
```
Python 3.12 + Flask       - Lightweight, flexible web framework
Flask-CORS                - Cross-origin resource sharing
Python-dotenv             - Environment variable management
Boto3 SDK                 - AWS services integration
OpenAI Python SDK         - GPT model integration
WeasyPrint                - PDF generation from HTML/CSS
MySQL Connector           - Database connectivity
```

### AI & Cloud Services
```
AWS Textract              - Document analysis and data extraction
OpenAI GPT-3.5/4          - Natural language processing and generation
AWS S3                    - Secure document storage
MySQL                     - Relational data persistence
```


## ⚙Installation & Setup

### Prerequisites

Before starting, ensure you have:

- **Python 3.9+** (developed with 3.12)
- **Node.js 16+** and npm/yarn
- **MySQL Server** (local or remote)
- **AWS Account** with:
  - S3 bucket for invoice storage
  - IAM user with Textract and S3 permissions
- **OpenAI API Key** with sufficient credits

### 1. Project Setup

```bash
# Clone the repository
git clone https://github.com/BryanHE24/InvoxAI/
cd InvoxAI

# Verify project structure
ls -la
# Should show: backend/ frontend/ README.md
```

### 2. Backend Configuration

```bash
# Create and activate virtual environment
python3 -m venv backend/venv
source backend/venv/bin/activate  # On Windows: backend\venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

#### Database Setup

```bash
# Connect to MySQL as root
mysql -u root -p

# Execute schema (creates database, user, and tables)
mysql -u root -p < backend/database/schema.sql
```

#### d. Environment Configuration

Create `backend/.env`:

```env
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your_super_secret_key_change_this_in_production

# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-invoice-bucket-name

# Database Configuration
DB_CONNECTION_TYPE=mysql+mysqlconnector
DB_HOST=localhost
DB_PORT=3306
DB_DATABASE=invoxdb
DB_USERNAME=developer
DB_PASSWORD=developer

# OpenAI Configuration
OPENAI_API_KEY=sk-your_openai_api_key_here
```

#### e. Configure Flask CLI Environment Variables (Project Root)

In your **project root directory** (`invoxAI/`), create a file named `.flaskenv` (if it doesn't exist). Add the following lines:

```env
FLASK_APP="backend.app:create_app()"
FLASK_ENV="development"
```

### 3. Frontend Configuration

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Launch Application

```bash
# Terminal 1: Start backend (from project root)
source backend/venv/bin/activate
flask run

# Terminal 2: Start frontend (from frontend/)
npm run dev
```

Access the application:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:5000

## Usage Guide

### Getting Started

1. **Upload Your First Invoice**
   - Navigate to "Upload Invoice"
   - Select PDF, JPG, or PNG files
   - Wait for processing confirmation

2. **Process with AI**
   - Go to "View Invoices"
   - Click "Process Result" on uploaded invoices
   - Review extracted data accuracy

3. **Explore Analytics**
   - Visit the Dashboard for spending insights
   - View interactive charts and AI-generated summaries
   - Export reports for external use

4. **Chat with Your Data**
   - Use the floating chat bubble
   - Ask natural language questions
   - Get instant insights about your financial data

### Pro Tips

- **Bulk Processing**: Upload multiple invoices before processing to batch operations
- **Category Management**: Consistently categorize invoices for better analytics
- **Regular Reports**: Generate monthly reports for accounting and tax purposes
- **AI Assistant**: Leverage the chatbot for quick data queries during meetings

## API Documentation

### Core Endpoints

```http
# Invoice Management
POST   /api/invoices/upload          # Upload new invoice
GET    /api/invoices                 # List all invoices
GET    /api/invoices/{id}            # Get invoice details
POST   /api/invoices/{id}/process    # Process with Textract
DELETE /api/invoices/{id}            # Delete invoice

# Analytics
GET    /api/analytics/dashboard      # Dashboard KPIs and charts
GET    /api/analytics/insights       # AI-generated insights

# Reports
POST   /api/reports/monthly          # Generate monthly report
POST   /api/reports/comprehensive    # Generate overview report
POST   /api/reports/export-pdf       # Export report as PDF

# AI Assistant
POST   /api/chat/query               # Send chat query
GET    /api/chat/context            # Get conversation context
```

### Response Examples

```json
{
  "invoice": {
    "id": 123,
    "filename": "invoice_001.pdf",
    "vendor_name": "TechCorp Solutions",
    "invoice_number": "INV-2024-001",
    "total_amount": 1250.00,
    "currency": "USD",
    "invoice_date": "2024-01-15",
    "status": "processed",
    "category": "Software & Tools",
    "line_items": [
      {
        "description": "Annual Software License",
        "amount": 1000.00,
        "quantity": 1
      }
    ]
  }
}
```

## DEMO
https://github.com/user-attachments/assets/8c0c8160-c69c-4f11-969a-de9fccc46b00

