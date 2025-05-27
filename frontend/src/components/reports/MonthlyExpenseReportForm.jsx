// frontend/src/components/reports/MonthlyExpenseReportForm.jsx
import React, { useState, useEffect } from 'react';
import reportService from '../../services/reportService';
import ReactMarkdown from 'react-markdown'; // To render Markdown
import remarkGfm from 'remark-gfm'; // For GitHub Flavored Markdown (tables, etc.)
import './ReportStyles.css'; // Shared styles for reports

const MonthlyExpenseReportForm = () => {
  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().getMonth() + 1; // JavaScript months are 0-indexed

  const [year, setYear] = useState(currentYear);
  const [month, setMonth] = useState(currentMonth);
  const [vendorFilter, setVendorFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  
  const [reportMarkdown, setReportMarkdown] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  // Populate years for dropdown
  const years = [];
  for (let y = currentYear + 1; y >= currentYear - 5; y--) {
    years.push(y);
  }
  const months = [
    { value: 1, label: 'January' }, { value: 2, label: 'February' },
    { value: 3, label: 'March' }, { value: 4, label: 'April' },
    { value: 5, label: 'May' }, { value: 6, label: 'June' },
    { value: 7, label: 'July' }, { value: 8, label: 'August' },
    { value: 9, label: 'September' }, { value: 10, label: 'October' },
    { value: 11, label: 'November' }, { value: 12, label: 'December' },
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setMessage('');
    setReportMarkdown('');

    try {
      const filters = {};
      if (vendorFilter.trim()) filters.vendor_name = vendorFilter.trim();
      if (categoryFilter.trim()) filters.category = categoryFilter.trim();

      const result = await reportService.generateMonthlyExpenseReport(year, month, filters);
      if (result.report_markdown) {
        setReportMarkdown(result.report_markdown);
        setMessage(result.message || 'Report generated successfully.');
      } else if (result.error) {
        setError(result.error + (result.details ? ` (${result.details})` : ''));
      } else {
        setError('Unexpected response from server.');
      }
    } catch (err) {
      console.error("Report generation error:", err);
      setError(err.message || err.error || 'Failed to generate report.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="report-form-container">
      <h3>Generate Monthly Expense Report</h3>
      <form onSubmit={handleSubmit} className="report-form">
        <div className="form-row">
            <div className="form-group">
            <label htmlFor="year">Year:</label>
            <select id="year" value={year} onChange={(e) => setYear(parseInt(e.target.value))} disabled={isLoading}>
                {years.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
            </div>
            <div className="form-group">
            <label htmlFor="month">Month:</label>
            <select id="month" value={month} onChange={(e) => setMonth(parseInt(e.target.value))} disabled={isLoading}>
                {months.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
            </select>
            </div>
        </div>
        <div className="form-row">
            <div className="form-group">
                <label htmlFor="vendorFilter">Vendor (Optional):</label>
                <input 
                    type="text" 
                    id="vendorFilter" 
                    value={vendorFilter} 
                    onChange={(e) => setVendorFilter(e.target.value)}
                    placeholder="e.g., Dell"
                    disabled={isLoading}
                />
            </div>
            <div className="form-group">
                <label htmlFor="categoryFilter">Category (Optional):</label>
                <input 
                    type="text" 
                    id="categoryFilter" 
                    value={categoryFilter} 
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    placeholder="e.g., Software"
                    disabled={isLoading}
                />
            </div>
        </div>
        <button type="submit" className="generate-report-button" disabled={isLoading}>
          {isLoading ? 'Generating...' : 'Generate Report'}
        </button>
      </form>

      {message && !error && <p className="report-message success">{message}</p>}
      {error && <p className="report-message error">{error}</p>}

      {reportMarkdown && (
        <div className="report-preview-section">
          <h4>Report Preview (Markdown Rendered)</h4>
          <div className="markdown-content report-content-styling"> {/* Added report-content-styling */}
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

export default MonthlyExpenseReportForm;