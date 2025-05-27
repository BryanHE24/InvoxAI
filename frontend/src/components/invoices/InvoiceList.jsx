// frontend/src/components/invoices/InvoiceList.jsx
import React from 'react';
import { Link } from 'react-router-dom';
import './InvoiceList.css';

const InvoiceList = ({ invoices, onProcessTextract, onConfirmDelete }) => {
  if (!invoices || invoices.length === 0) {
    return <p className="no-invoices-message">No invoices found. Try uploading some!</p>;
  }

  const formatDateForList = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      const parts = dateString.split('-');
      if (parts.length === 3) return dateString;
      const dateObj = new Date(dateString);
      if (isNaN(dateObj.getTime())) return dateString;
      return dateObj.toLocaleDateString('en-CA');
    } catch (e) { return dateString; }
  };

  const formatCurrency = (amount, currency) => {
    if (typeof amount !== 'number') return 'N/A';
    const displayCurrency = currency || '$'; // Default to $ if no currency provided
    return `${displayCurrency}${amount.toFixed(2)}`;
  };

  return (
    <div className="invoice-list-container card-invo"> 
      <div className="table-responsive-container">
        <table className="invoice-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Filename</th>
              <th>Vendor</th>
              <th>Inv. Date</th>
              <th>Total</th>
              <th>Status</th>
              <th style={{textAlign: 'right'}}>Actions</th> {/* Align header to match buttons */}
            </tr>
          </thead>
          <tbody>
            {invoices.map((invoice) => (
              <tr key={invoice.id}>
                <td>{invoice.id}</td>
                <td>
                  {invoice.original_filename ? (
                    <Link to={`/invoices/${invoice.id}`} title={`View details for ${invoice.original_filename}`}>
                      {invoice.original_filename.length > 30 
                        ? `${invoice.original_filename.substring(0, 27)}...` 
                        : invoice.original_filename}
                    </Link>
                  ) : 'N/A'}
                </td>
                <td>{invoice.vendor_name || 'N/A'}</td>
                <td>{formatDateForList(invoice.invoice_date)}</td>
                <td>{formatCurrency(invoice.total_amount, invoice.currency)}</td>
                <td>
                  <span className={`status-badge status-${invoice.status?.toLowerCase().replace(/_/g, '-')}`}>
                    {invoice.status ? invoice.status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'Unknown'}
                  </span>
                </td>
                <td className="invoice-actions">
                  <Link 
                    to={`/invoices/${invoice.id}`} 
                    className="action-button view-button" // More neutral style
                  >
                    View
                  </Link>
                  {invoice.status === 'processing_textract' && invoice.textract_job_id && (
                    <button 
                      onClick={() => onProcessTextract(invoice.id)} 
                      className="action-button process-button" // Positive action style
                      title={`Process Textract Job: ${invoice.textract_job_id}`}
                    >
                      Process
                    </button>
                  )}
                  <button 
                      onClick={() => onConfirmDelete(invoice.id, invoice.original_filename)} 
                      className="action-button delete-button" // Danger action style
                      title={`Delete invoice ${invoice.id}`}
                  >
                      Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default InvoiceList;