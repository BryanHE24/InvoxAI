// frontend/src/pages/InvoicesPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import InvoiceList from '../components/invoices/InvoiceList.jsx'; // Ensure this path is correct
import invoiceService from '../services/invoiceService';
import './InvoicesPage.css'; 

const InvoicesPage = () => {
  const [invoices, setInvoices] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [processMessage, setProcessMessage] = useState('');
  const [deleteMessage, setDeleteMessage] = useState('');

  const fetchInvoices = useCallback(async () => {
    setIsLoading(true); setError(null); setProcessMessage(''); setDeleteMessage(''); 
    console.log("InvoicesPage: Calling fetchInvoices...");
    try {
      const data = await invoiceService.getAllInvoices();
      console.log("InvoicesPage: Data received by fetchInvoices (before setInvoices):", JSON.stringify(data, null, 2));
      console.log("InvoicesPage: Number of invoices received:", data ? data.length : 'null/undefined');
      setInvoices(data || []); 
    } catch (err) {
      console.error("InvoicesPage: Error in fetchInvoices catch block:", err); 
      setError(err.message || err.error || 'Failed to fetch invoices.');
      setInvoices([]); 
    } finally {
      setIsLoading(false);
      console.log("InvoicesPage: fetchInvoices finished.");
    }
  }, []);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]); 

  const handleProcessTextract = async (invoiceId) => {
    setProcessMessage(`Processing Textract for invoice ID: ${invoiceId}...`);
    setError(null); setDeleteMessage('');
    try {
      const result = await invoiceService.processTextractResult(invoiceId);
      setProcessMessage(result.message || `Successfully triggered processing for ${invoiceId}.`);
      fetchInvoices(); 
    } catch (err) {
      setProcessMessage(''); 
      setError(err.response?.data?.error || err.message || `Failed to process Textract for ID: ${invoiceId}.`);
    }
    setTimeout(() => setProcessMessage(''), 5000);
  };

  const handleConfirmDelete = async (invoiceId, filename) => {
    setDeleteMessage(''); setError(null); setProcessMessage('');
    if (window.confirm(`Are you sure you want to delete invoice "${filename || 'N/A'}" (ID: ${invoiceId})? This action cannot be undone.`)) {
      try {
        const result = await invoiceService.deleteInvoice(invoiceId);
        setDeleteMessage(result.message || `Invoice ${invoiceId} deleted.`);
        fetchInvoices(); 
      } catch (err) {
        console.error("Delete invoice error:", err);
        setDeleteMessage(err.error || err.message || `Failed to delete invoice ${invoiceId}.`);
      }
      setTimeout(() => setDeleteMessage(''), 5000);
    }
  };

  if (isLoading && invoices.length === 0) { // Show loading only on initial load
    return <div className="loading-message card-invo">Loading invoices...</div>;
  }

  const actionMessage = deleteMessage || processMessage;
  const isActionError = (deleteMessage && (deleteMessage.startsWith('Error') || deleteMessage.startsWith('Failed'))) || 
                       (processMessage && (processMessage.startsWith('Error') || processMessage.startsWith('Failed')));

  return (
    <div className="invoices-page-container">
      <div className="page-header-invo"> {/* Using new class for consistency */}
        <h1>All Invoices</h1>
        <button 
            onClick={fetchInvoices} 
            className="refresh-button button-secondary" /* Using button class from index.css */
            disabled={isLoading}
        >
          {isLoading ? 'Refreshing...' : 'Refresh List'}
        </button>
      </div>

      {error && (!invoices || invoices.length === 0) && /* Show main error if list is empty and error occurred */
        <p className="error-message card-invo">{error}</p> 
      }
      {actionMessage && (
         <p className={`action-feedback-message ${isActionError ? 'error-message' : 'success-message'} card-invo`}>
            {actionMessage}
         </p>
      )}
      
      <InvoiceList 
        invoices={invoices} 
        onProcessTextract={handleProcessTextract}
        onConfirmDelete={handleConfirmDelete}
      />
    </div>
  );
};
export default InvoicesPage;