// frontend/src/pages/UploadPage.jsx
import React from 'react';
import UploadForm from '../components/upload/UploadForm.jsx'; // Ensure .jsx
import './UploadPage.css';

const UploadPage = () => {
  return (
    <div className="upload-page-invo"> {/* Page specific container */}
      <div className="page-header-invo"> {/* Consistent page header style */}
        <h1>Upload New Invoice</h1>
      </div>
      <UploadForm />
    </div>
  );
};

export default UploadPage;