// frontend/src/services/reportService.js
import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api/reports'; // Base URL for report endpoints

const reportService = {
  generateMonthlyExpenseReport: async (year, month, filters = {}) => {
    try {
      const payload = { year, month, ...filters }; // Include optional vendor_name, category
      const response = await axios.post(`${API_BASE_URL}/generate/monthly-expense`, payload);
      // Expected response: { report_markdown: "...", message: "..." } or { error: "...", details: "..." }
      return response.data;
    } catch (error) {
      console.error('Error generating monthly expense report:', error);
      // Ensure a consistent error object is thrown
      const errorData = error.response?.data || { error: "Network error or an unexpected issue occurred when generating monthly report." };
      if (!errorData.message && errorData.error) errorData.message = errorData.error; // Use .error as .message if .message is missing
      else if (!errorData.message && !errorData.error) errorData.message = "Unknown error generating monthly report.";
      throw errorData;
    }
  },

  // --- ADDED THIS FUNCTION ---
  generateComprehensiveOverviewReport: async () => {
    try {
      // This endpoint in the backend is POST /api/reports/generate/comprehensive-overview
      // It currently doesn't require a body, but POST is appropriate for a generation task.
      const response = await axios.post(`${API_BASE_URL}/generate/comprehensive-overview`, {}); 
      return response.data; // Expected: { report_markdown: "...", message: "..." } or { error: "..." }
    } catch (error) {
      console.error('Error generating comprehensive overview report:', error);
      const errorData = error.response?.data || { error: "Network error or an unexpected issue occurred when generating comprehensive report." };
      if (!errorData.message && errorData.error) errorData.message = errorData.error;
      else if (!errorData.message && !errorData.error) errorData.message = "Unknown error generating comprehensive report.";
      throw errorData;
    }
  }
  // --- END ADDED FUNCTION ---

  // Placeholder for PDF export later
  // downloadMonthlyExpenseReportPDF: async (year, month, filters = {}) => { /* ... */ }
};

export default reportService;
