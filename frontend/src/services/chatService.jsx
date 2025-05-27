// frontend/src/services/chatService.js
import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api'; // Your Flask backend URL

const chatService = {
  sendMessage: async (message, sessionId = 'default_session') => { // sessionId can be enhanced later
    try {
      const response = await axios.post(`${API_BASE_URL}/chat/`, {
        message: message,
        session_id: sessionId, // Pass session_id if your backend uses it
      });
      // Expected response: { reply: "Assistant's message" }
      return response.data;
    } catch (error) {
      console.error('Error sending chat message:', error);
      if (error.response && error.response.data && error.response.data.error) {
        throw new Error(error.response.data.error); // Throw backend error message
      }
      throw new Error(error.message || 'Failed to send message or get reply from chat assistant.');
    }
  },
};

export default chatService;