// frontend/src/pages/ReportsPage.jsx
import React from 'react';
import MonthlyExpenseReportForm from '../components/reports/MonthlyExpenseReportForm.jsx';
import ComprehensiveReportSection from '../components/reports/ComprehensiveReportSection.jsx'; // Import new component
import './ReportsPage.css';

const ReportsPage = () => {
  return (
    <div className="reports-page-container">
      <div className="page-header">
        <h1>Reports Center</h1>
        <p className="page-subtitle">
          Generate and view detailed financial reports.
        </p>
      </div>
      
      <MonthlyExpenseReportForm />

      <hr className="report-section-divider" /> {/* Optional divider */}

      <ComprehensiveReportSection />
      
    </div>
  );
};

export default ReportsPage;