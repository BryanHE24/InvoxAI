// frontend/src/pages/ViewInvoicePage.jsx
import React from 'react';
import { useParams } from 'react-router-dom';
import InvoiceDetail from '../components/invoices/InvoiceDetail'; // Import the new component
import './ViewInvoicePage.css'; // Create for page-specific styles if needed

const ViewInvoicePage = () => {
  const { id } = useParams(); // Gets the :id from the URL (e.g., /invoices/3 -> id is "3")

  return (
    <div className="view-invoice-page-container">
      {/* <h1>Invoice Details</h1> // Title can be inside InvoiceDetail */}
      <InvoiceDetail invoiceId={id} />
    </div>
  );
};

export default ViewInvoicePage;