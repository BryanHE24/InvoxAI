// frontend/src/components/invoices/InvoiceDetail.jsx
import React, { useState, useEffect, useCallback } from 'react';
import invoiceService from '../../services/invoiceService';
import './InvoiceDetail.css';

const PREDEFINED_CATEGORIES = [
    "Software", "Hardware", "Cloud Services", "Office Supplies", 
    "Travel", "Marketing", "Consulting", "Utilities", "Legal", "Other"
];

const InvoiceDetail = ({ invoiceId }) => {
  const [invoice, setInvoice] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [s3ViewUrl, setS3ViewUrl] = useState(null);
  const [isLoadingUrl, setIsLoadingUrl] = useState(false);
  const [isEditingCategory, setIsEditingCategory] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [categoryUpdateMessage, setCategoryUpdateMessage] = useState('');

  const fetchInvoiceData = useCallback(async () => {
    if (!invoiceId) return;
    setIsLoading(true);
    setError(null);
    setCategoryUpdateMessage('');
    try {
      const data = await invoiceService.getInvoiceById(invoiceId);
      
      // --- ADDED CONSOLE LOGS FOR DEBUGGING DATES ---
      console.log("InvoiceDetail: Raw data received from API:", JSON.stringify(data, null, 2));
      console.log("InvoiceDetail: API invoice_date:", data.invoice_date, "| Type:", typeof data.invoice_date);
      console.log("InvoiceDetail: API due_date:", data.due_date, "| Type:", typeof data.due_date);
      // --- END ADDED CONSOLE LOGS ---

      setInvoice(data);
      setSelectedCategory(data?.user_category || '');
    } catch (err) {
      const errorMsg = err?.response?.data?.error || err?.message || `Failed to fetch invoice ${invoiceId}.`;
      setError(errorMsg);
      console.error("Fetch Invoice Data Error:", err);
    } finally {
      setIsLoading(false);
    }
  }, [invoiceId]);

  useEffect(() => {
    fetchInvoiceData();
  }, [fetchInvoiceData]); // fetchInvoiceData is memoized and includes invoiceId

  const fetchS3ViewUrl = async () => {
    if (!invoice || !invoice.s3_key) return;
    setIsLoadingUrl(true);
    setCategoryUpdateMessage('');
    try {
      const response = await invoiceService.getInvoiceViewUrl(invoiceId); 
      setS3ViewUrl(response.view_url);
    } catch (err) {
      console.error("Error fetching S3 view URL:", err);
      const errorMsg = err?.response?.data?.error || err?.message || "Could not load S3 preview URL.";
      setCategoryUpdateMessage(`Error: ${errorMsg}`);
    } finally {
      setIsLoadingUrl(false);
    }
  };

  const handleCategoryChange = (e) => {
    setSelectedCategory(e.target.value);
  };

  const handleSaveCategory = async () => {
    if (!invoice || selectedCategory === (invoice.user_category || '')) {
      setIsEditingCategory(false);
      setCategoryUpdateMessage('');
      return;
    }
    setCategoryUpdateMessage('Updating category...');
    try {
      const updateData = { user_category: selectedCategory === '' ? null : selectedCategory };
      const updatedInvoiceResponse = await invoiceService.updateInvoice(invoice.id, updateData);
      setInvoice(updatedInvoiceResponse.invoice); 
      setSelectedCategory(updatedInvoiceResponse.invoice.user_category || '');
      setCategoryUpdateMessage('Category updated successfully!');
      setIsEditingCategory(false);
    } catch (err) {
      console.error("Error updating category:", err);
      const errorMessage = err?.error || err?.message || 'Failed to update category.';
      setCategoryUpdateMessage(`Error: ${errorMessage}`);
    }
    setTimeout(() => setCategoryUpdateMessage(''), 4000);
  };
  
  // --- REVISED formatDate FUNCTION ---
  const formatDate = (dateString) => {
    if (!dateString || typeof dateString !== 'string') {
      // console.log("formatDate: Received non-string or empty input:", dateString);
      return 'N/A'; 
    }
    // At this point, dateString should be a 'YYYY-MM-DD' string from backend
    try {
      const parts = dateString.split('-');
      if (parts.length !== 3) {
        console.warn("formatDate: dateString is not in YYYY-MM-DD format:", dateString);
        return 'Invalid Date Str'; // Indicates it wasn't YYYY-MM-DD
      }
      // year, month (0-indexed), day
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1; // Month is 0-indexed in JS Date
      const day = parseInt(parts[2], 10);

      // Validate parsed parts
      if (isNaN(year) || isNaN(month) || isNaN(day)) {
        console.warn("formatDate: parsed date parts are NaN:", dateString, year, month, day);
        return 'Invalid Date Parts';
      }

      // Create as UTC date to avoid timezone interpretation of YYYY-MM-DD
      const dateObj = new Date(Date.UTC(year, month, day)); 

      if (isNaN(dateObj.getTime())) { 
          console.warn("formatDate: new Date(Date.UTC(...)) resulted in Invalid Date for parts:", year, month, day, "from original:", dateString);
          return 'Invalid Date Build'; 
      }
      // Display in user's locale, based on the UTC date
      return dateObj.toLocaleDateString(undefined, { 
        year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' 
      });
    } catch (e) {
      console.error("Error in formatDate function for:", dateString, e);
      return 'Date Fmt Err'; 
    }
  };
  // --- END REVISED formatDate ---

  const formatTimestamp = (timestampString) => {
    if (!timestampString) return 'N/A';
    try {
      return new Date(timestampString).toLocaleString(undefined, {
        year: 'numeric', month: 'long', day: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit'
      });
    } catch(e) { return timestampString; }
  }

  const renderJsonData = (data, title) => {
    if (data === null || data === undefined) return <div className="json-data-section"><h4>{title}</h4><p className="no-data-message">N/A</p></div>;
    let jsonData = data;
    if (typeof data === 'string') {
      try { jsonData = JSON.parse(data); } 
      catch (e) { return <div className="json-data-section"><h4>{title} (Raw String)</h4><pre>{data}</pre></div>; }
    }
    if (jsonData === null || jsonData === undefined || (Array.isArray(jsonData) && jsonData.length === 0) || (typeof jsonData === 'object' && Object.keys(jsonData).length === 0) ) {
        return <div className="json-data-section"><h4>{title}</h4><p className="no-data-message">N/A</p></div>;
    }
    return (
      <div className="json-data-section">
        <h4>{title}</h4>
        <pre>{JSON.stringify(jsonData, null, 2)}</pre>
      </div>
    );
  };

  const renderLineItemsTable = (lineItems) => {
    if (!lineItems || !Array.isArray(lineItems) || lineItems.length === 0) {
      return <div className="line-items-section"><h3>Line Items</h3><p className="no-data-message">No line items extracted or available.</p></div>;
    }
    const headers = ['Description', 'Quantity', 'Unit Price', 'Amount', 'Product Code'];
    const keyMap = {
        'Description': 'description', 'Quantity': 'quantity',
        'Unit Price': 'unit_price', 'Amount': 'amount', 
        'Product Code': 'product_code'
    };
    return (
      <div className="line-items-section">
        <h3>Line Items</h3>
        <div className="table-responsive-container">
          <table className="line-items-table">
            <thead><tr>{headers.map(header => <th key={header}>{header}</th>)}</tr></thead>
            <tbody>
              {lineItems.map((item, index) => (
                <tr key={item.id || item.description || index}> 
                  {headers.map(header => {
                    const itemKey = keyMap[header];
                    let cellValue = item[itemKey];
                    if (['Unit Price', 'Amount', 'Quantity'].includes(header) && typeof cellValue === 'number') {
                      // For quantity, don't add currency symbol. For amounts, do.
                      if (header === 'Quantity') {
                        cellValue = cellValue.toFixed(itemKey === 'quantity' ? 0 : 2); // quantity may not need decimals
                      } else {
                        cellValue = `${invoice?.currency || '$'}${cellValue.toFixed(2)}`;
                      }
                    } else if (cellValue === null || cellValue === undefined) {
                      cellValue = 'N/A';
                    }
                    return <td key={`${header}-${index}`}>{String(cellValue)}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  if (isLoading) return <p className="loading-message">Loading invoice details...</p>;
  if (error && !invoice) return <p className="error-message">Error: {error}</p>; 
  if (!invoice) return <p className="no-data-message">Invoice data not found.</p>;

  return (
    <div className="invoice-detail-container">
      {error && !isLoading && <p className="error-message inline-error">Notice: {error}</p>}
      <div className="invoice-header">
        <h2>Invoice: {invoice.original_filename || `ID ${invoice.id}`}</h2>
        <span className={`status-badge status-${invoice.status?.toLowerCase().replace(/_/g, '-')}`}>
          Status: {invoice.status ? invoice.status.replace(/_/g, ' ') : 'Unknown'}
        </span>
      </div>
      {invoice.error_message && <p className="error-message-detail">Processing Error: {invoice.error_message}</p>}
      <div className="invoice-metadata-grid">
        <div className="metadata-item"><strong>Invoice ID:</strong> {invoice.id}</div>
        <div className="metadata-item"><strong>Filename:</strong> {invoice.original_filename || 'N/A'}</div>
        <div className="metadata-item"><strong>Uploaded:</strong> {formatTimestamp(invoice.upload_timestamp)}</div>
        <div className="metadata-item"><strong>Last Modified:</strong> {formatTimestamp(invoice.last_modified_timestamp)}</div>
        {invoice.s3_bucket_name && <div className="metadata-item"><strong>S3 Bucket:</strong> {invoice.s3_bucket_name}</div>}
        {invoice.s3_key && (
          <div className="metadata-item s3-key-item">
            <strong>S3 Key:</strong> <span className="s3-key-text">{invoice.s3_key}</span>
            <button onClick={fetchS3ViewUrl} disabled={isLoadingUrl || s3ViewUrl} className="s3-link-button">
              {isLoadingUrl ? "Loading..." : (s3ViewUrl ? "Link Loaded" : "Get S3 Link")}
            </button>
            {s3ViewUrl && <a href={s3ViewUrl} target="_blank" rel="noopener noreferrer" className="s3-view-link">Open File</a>}
          </div>
        )}
        {invoice.textract_job_id && <div className="metadata-item"><strong>Textract Job ID:</strong> {invoice.textract_job_id}</div>}
      </div>
      <h3>Extracted Information</h3>
      <div className="invoice-extracted-data-grid">
        <div className="extracted-item"><strong>Vendor:</strong> {invoice.vendor_name || 'N/A'}</div>
        <div className="extracted-item"><strong>Invoice Number:</strong> {invoice.invoice_id_number || 'N/A'}</div>
        <div className="extracted-item"><strong>Invoice Date:</strong> {formatDate(invoice.invoice_date)}</div>
        <div className="extracted-item"><strong>Due Date:</strong> {formatDate(invoice.due_date)}</div>
        <div className="extracted-item"><strong>Total Amount:</strong> {typeof invoice.total_amount === 'number' ? `${invoice.currency || '$'}${invoice.total_amount.toFixed(2)}` : 'N/A'}</div>
        <div className="extracted-item"><strong>Subtotal:</strong> {typeof invoice.subtotal === 'number' ? `${invoice.currency || '$'}${invoice.subtotal.toFixed(2)}` : 'N/A'}</div>
        <div className="extracted-item"><strong>Tax:</strong> {typeof invoice.tax === 'number' ? `${invoice.currency || '$'}${invoice.tax.toFixed(2)}` : 'N/A'}</div>
      </div>
      <div className="invoice-category-section">
        <h3>Category</h3>
        {isEditingCategory ? (
          <div className="category-edit-form">
            <select value={selectedCategory} onChange={handleCategoryChange} className="category-select">
              <option value="">-- Uncategorized --</option>
              {PREDEFINED_CATEGORIES.map(cat => (<option key={cat} value={cat}>{cat}</option>))}
            </select>
            <input type="text" value={selectedCategory} onChange={handleCategoryChange} placeholder="Or type a custom category" className="category-custom-input" list="predefined-categories-datalist"/>
            <datalist id="predefined-categories-datalist">{PREDEFINED_CATEGORIES.map(cat => (<option key={cat} value={cat}/>))}</datalist>
            <button onClick={handleSaveCategory} className="category-save-button">Save</button>
            <button onClick={() => { setIsEditingCategory(false); setSelectedCategory(invoice.user_category || '');}} className="category-cancel-button">Cancel</button>
          </div>
        ) : (
          <div className="category-display">
            <p>{invoice.user_category || 'Not Categorized'}</p>
            <button onClick={() => setIsEditingCategory(true)} className="category-edit-button">
              {invoice.user_category ? 'Edit Category' : 'Add Category'}
            </button>
          </div>
        )}
        {categoryUpdateMessage && <p className={`category-update-message ${categoryUpdateMessage.startsWith('Error:') ? 'message-error' : 'message-success'}`}>{categoryUpdateMessage}</p>}
      </div>
      {renderLineItemsTable(invoice.line_items)}
      <br></br>
      {renderJsonData(invoice.parsed_data, "Detailed Parsed Data (Summary Fields from AnalyzeExpense)")}
      {s3ViewUrl && (invoice.s3_key?.toLowerCase().endsWith('.pdf') || invoice.s3_key?.toLowerCase().endsWith('.png') || invoice.s3_key?.toLowerCase().endsWith('.jpg') || invoice.s3_key?.toLowerCase().endsWith('.jpeg')) && (
        <div className="invoice-preview-container">
          <h4>Invoice Preview</h4>
          {invoice.s3_key?.toLowerCase().endsWith('.pdf') ? (
            <iframe src={s3ViewUrl} title="Invoice PDF Preview" width="100%" height="700px" style={{ border: '1px solid #ccc' }}></iframe>
          ) : (
            <img src={s3ViewUrl} alt="Invoice Preview" style={{ maxWidth: '100%', border: '1px solid #ccc' }} />
          )}
        </div>
      )}
    </div>
  );
};

export default InvoiceDetail;