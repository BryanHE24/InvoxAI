// frontend/src/services/invoiceService.js
import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

const invoiceService = {
  getAllInvoices: async () => {
    try {
      console.log("invoiceService: Requesting GET /api/invoices/"); // LOG BEFORE CALL
      const response = await axios.get(`${API_BASE_URL}/invoices/`);
      // LOG THE ACTUAL DATA RECEIVED FROM BACKEND
      console.log("invoiceService.getAllInvoices response.status:", response.status);
      console.log("invoiceService.getAllInvoices response.data:", JSON.stringify(response.data, null, 2)); 
      return Array.isArray(response.data) ? response.data : [];
    } catch (error) {
      console.error('Error fetching all invoices from invoiceService:', error.response || error);
      // Rethrow a more structured error or the one from backend if available
      const errorData = error.response?.data || { error: "Network error or an unexpected issue occurred." };
      if (!errorData.message && errorData.error) errorData.message = errorData.error;
      else if (!errorData.message && !errorData.error) errorData.message = "Unknown error fetching invoices.";
      throw errorData;
    }
  },

  getInvoiceById: async (id) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/invoices/${id}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching invoice with ID ${id}:`, error.response || error);
      throw error.response?.data || error;
    }
  },

  getInvoiceViewUrl: async (invoiceId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/invoices/${invoiceId}/view-url`);
      return response.data; 
    } catch (error) {
      console.error(`Error fetching S3 view URL for invoice ID ${invoiceId}:`, error.response || error);
      throw error.response?.data || error;
    }
  },

  processTextractResult: async (invoiceId) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/invoices/${invoiceId}/process-textract-result`);
      return response.data;
    } catch (error) {
      console.error(`Error processing Textract result for invoice ID ${invoiceId}:`, error.response || error);
      throw error.response?.data || error;
    }
  },

  updateInvoice: async (invoiceId, updateData) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/invoices/${invoiceId}`, updateData);
      return response.data; 
    } catch (error) {
      console.error(`Error updating invoice ID ${invoiceId}:`, error.response || error);
      throw error.response?.data || error;
    }
  },

  deleteInvoice: async (invoiceId) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/invoices/${invoiceId}`);
      return response.data; 
    } catch (error) {
      console.error(`Error deleting invoice ID ${invoiceId}:`, error.response || error);
      throw error.response?.data || error;
    }
  },
};

export default invoiceService;