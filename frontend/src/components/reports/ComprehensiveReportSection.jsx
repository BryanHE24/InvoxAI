// frontend/src/components/reports/ComprehensiveReportSection.jsx
import React, { useState } from 'react';
import reportService from '../../services/reportService';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './ReportStyles.css'; // Shared styles

const ComprehensiveReportSection = () => {
  const [reportMarkdown, setReportMarkdown] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const handleGenerateReport = async () => {
    setIsLoading(true);
    setError('');
    setMessage('');
    setReportMarkdown('');
    try {
      const result = await reportService.generateComprehensiveOverviewReport();
      if (result.report_markdown) {
        setReportMarkdown(result.report_markdown);
        setMessage(result.message || 'Comprehensive report generated successfully.');
      } else if (result.error) {
        setError(result.error + (result.details ? ` (${result.details})` : ''));
      } else {
        setError('Unexpected response from server when generating comprehensive report.');
      }
    } catch (err) {
      console.error("Comprehensive report generation error:", err);
      setError(err.message || err.error || 'Failed to generate comprehensive report.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="report-form-container"> {/* Re-using class for similar styling */}
      <h3>Generate Comprehensive Overview Report</h3>
      <p>This report provides an overview of all processed invoice data in the system.</p>
      <button onClick={handleGenerateReport} className="generate-report-button" disabled={isLoading}>
        {isLoading ? 'Generating Overview...' : 'Generate Comprehensive Overview'}
      </button>

      {message && !error && <p className="report-message success">{message}</p>}
      {error && <p className="report-message error">{error}</p>}

      {reportMarkdown && (
        <div className="report-preview-section">
          <h4>Report Preview</h4>
          <div className="markdown-content report-content-styling">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {reportMarkdown}
            </ReactMarkdown>
          </div>
          {/* TODO: Add Export to PDF button here later */}
        </div>
      )}
    </div>
  );
};

export default ComprehensiveReportSection;