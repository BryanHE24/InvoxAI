// frontend/src/components/upload/UploadForm.jsx
import React, { useState, useRef } from 'react';
import axios from 'axios';
import './UploadForm.css'; // Will update this file

const API_BASE_URL = 'http://localhost:5000/api';

// Simple SVG Icon for upload
const UploadCloudIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="upload-icon">
    <polyline points="16 16 12 12 8 16"></polyline><line x1="12" y1="12" x2="12" y2="21"></line>
    <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"></path><polyline points="16 16 12 12 8 16"></polyline>
  </svg>
);


const UploadForm = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [uploadedInvoiceInfo, setUploadedInvoiceInfo] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = (event) => {
    if (event.target.files && event.target.files[0]) {
        setSelectedFile(event.target.files[0]);
        setMessage(''); setUploadedInvoiceInfo(null); setUploadProgress(0);
    }
  };

  const onFileInputAreaClick = () => { fileInputRef.current?.click(); };

  const handleDragOver = (event) => { event.preventDefault(); /* Necessary to allow drop */ };
  const handleDrop = (event) => {
    event.preventDefault();
    if (event.dataTransfer.files && event.dataTransfer.files[0]) {
      setSelectedFile(event.dataTransfer.files[0]);
      setMessage(''); setUploadedInvoiceInfo(null); setUploadProgress(0);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!selectedFile) { setMessage('Please select a file first.'); return; }
    setIsUploading(true); setMessage('Uploading...'); setUploadedInvoiceInfo(null);
    const formData = new FormData();
    formData.append('file', selectedFile);
    try {
      const response = await axios.post(`${API_BASE_URL}/invoices/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const percent = Math.round((progressEvent.loaded * 100) / (progressEvent.total || selectedFile.size));
          setUploadProgress(percent);
        },
      });
      setMessage(`Success: ${response.data.message}`);
      setUploadedInvoiceInfo(response.data);
      setSelectedFile(null); 
      if(fileInputRef.current) fileInputRef.current.value = "";
    } catch (error) {
      console.error('Upload error:', error);
      const errorMsg = error.response?.data?.error || error.message || 'Upload failed.';
      setMessage(`Error: ${errorMsg}`);
      setUploadedInvoiceInfo(null);
    } finally { setIsLoading(false); }
  };

  return (
    <div className="upload-form-card card-invo"> {/* Main card style */}
      <h2 className="upload-form-title">Upload Your Invoice</h2>
      <p className="upload-form-subtitle">Drag & drop or click to select a PDF, JPG, or PNG file.</p>
      
      <form onSubmit={handleSubmit}>
        <div 
          className={`file-drop-area ${isUploading ? 'uploading' : ''}`}
          onClick={onFileInputAreaClick}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          role="button" tabIndex={0}
          onKeyPress={(e) => { if (e.key === 'Enter' || e.key === ' ') onFileInputAreaClick();}}
        >
          <input
            ref={fileInputRef}
            type="file"
            id="invoiceFile-styled" // Different ID from basic one
            className="file-input-hidden"
            onChange={handleFileChange}
            accept=".pdf,.jpg,.jpeg,.png"
            disabled={isUploading}
            aria-label="Invoice file uploader"
          />
          <div className="file-drop-area-content">
            <UploadCloudIcon />
            {selectedFile ? (
              <p className="file-name-display">Selected: {selectedFile.name}</p>
            ) : (
              <p>Click to browse or drag file here</p>
            )}
          </div>
        </div>

        {selectedFile && !isUploading && (
          <div className="file-preview-info">
            <span>{selectedFile.name} ({(selectedFile.size / 1024).toFixed(2)} KB)</span>
          </div>
        )}

        <button 
            type="submit" 
            disabled={!selectedFile || isUploading} 
            className="button button-primary upload-submit-button"
        >
          {isUploading ? `Uploading... ${uploadProgress}%` : 'Upload & Process'}
        </button>
      </form>

      {isUploading && (
        <div className="upload-progress-bar-container">
          <div className="upload-progress-bar" style={{ width: `${uploadProgress}%` }}></div>
        </div>
      )}

      {message && (
        <p className={`upload-message ${uploadedInvoiceInfo || message.toLowerCase().includes("success") ? 'success' : 'error'}`}>
          {message}
        </p>
      )}

      {uploadedInvoiceInfo && (
        <div className="upload-result-info card-invo-nested">
          <h4>Upload Successful:</h4>
          <p><strong>Invoice ID:</strong> {uploadedInvoiceInfo.invoice_id}</p>
          <p><strong>Status:</strong> {uploadedInvoiceInfo.current_status}</p>
          <p><em>Textract processing initiated. You can check its status on the 'View Invoices' page or an invoice detail page later.</em></p>
        </div>
      )}
    </div>
  );
};
export default UploadForm;