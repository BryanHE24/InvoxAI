// frontend/src/services/analyticsService.js
import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api/analytics';

const analyticsService = {
  getSummary: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/summary`);
      return response.data;
    } catch (error) {
      console.error('Error fetching summary analytics:', error);
      throw error.response?.data || error;
    }
  },

  getExpensesByVendor: async (limit = 5) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/expenses-by-vendor?limit=${limit}`);
      return Array.isArray(response.data) ? response.data : [];
    } catch (error) {
      console.error('Error fetching expenses by vendor:', error);
      throw error.response?.data || error;
    }
  },

  getExpensesByCategory: async (limit = 5) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/expenses-by-category?limit=${limit}`);
      return Array.isArray(response.data) ? response.data : [];
    } catch (error) {
      console.error('Error fetching expenses by category:', error);
      throw error.response?.data || error;
    }
  },

  getMonthlySpend: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/monthly-spend`);
      return Array.isArray(response.data) ? response.data : [];
    } catch (error) {
      console.error('Error fetching monthly spend:', error);
      throw error.response?.data || error;
    }
  },

  getOpenAIDashboardSummary: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/openai-summary`);
      // Expected: { ai_insight_summary: "Text summary from AI..." } or { error: "...", details: "..." }
      return response.data; 
    } catch (error) {
      console.error('Error fetching AI dashboard summary (axios catch):', error);
      // Rethrow a structured error that the component can inspect
      const errorData = error.response?.data || { error: "Network error or an unexpected issue occurred while fetching AI summary." };
      // Ensure a message property exists for easier display
      if (typeof errorData === 'string') throw new Error(errorData);
      if (!errorData.message && errorData.error) errorData.message = errorData.error;
      else if (!errorData.message && !errorData.error) errorData.message = "Unknown error fetching AI summary.";
      throw errorData;
    }
  },
};

export default analyticsService;