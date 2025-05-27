// frontend/src/components/chatbot/Chatbot.jsx
import React, { useState, useEffect, useRef } from 'react';
import chatService from '../../services/chatService';
import './Chatbot.css';

const ChatIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20px" height="20px">
    <path d="M0 0h24v24H0z" fill="none"/>
    <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/>
  </svg>
);
const SendIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18px" height="18px">
    <path d="M0 0h24v24H0z" fill="none"/>
    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
  </svg>
);
const CloseIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20px" height="20px">
    <path d="M0 0h24v24H0z" fill="none"/>
    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
  </svg>
);


const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { id: Date.now(), sender: 'bot', text: 'Hello! How can I help you with your invoices today?' }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(''); // General error message if needed outside chat bubbles

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null); // Ref for the input field

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
      inputRef.current?.focus(); // Focus input when chat opens
    }
  }, [messages, isOpen]);

  const toggleChat = () => {
    setIsOpen(!isOpen);
    if (!isOpen) {
      setError(''); 
      // Optionally reset messages if desired on every open:
      // setMessages([{ id: Date.now(), sender: 'bot', text: 'Hello! How can I help you with your invoices today?' }]);
    }
  };

  const handleInputChange = (e) => {
    setInputValue(e.target.value);
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    const trimmedInput = inputValue.trim();
    if (!trimmedInput) return;

    const userMessage = { id: Date.now(), sender: 'user', text: trimmedInput };
    setMessages(prevMessages => [...prevMessages, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(''); // Clear previous general errors

    try {
      const response = await chatService.sendMessage(userMessage.text);
      const botMessage = { id: Date.now() + 1, sender: 'bot', text: response.reply || "I'm not sure how to respond to that." };
      setMessages(prevMessages => [...prevMessages, botMessage]);
    } catch (err) {
      console.error("Chatbot frontend error:", err);
      const errorMessageText = err.message || "Sorry, I couldn't connect to the assistant or an error occurred.";
      const errorBotMessage = { id: Date.now() + 1, sender: 'bot', text: errorMessageText, isError: true };
      setMessages(prevMessages => [...prevMessages, errorBotMessage]);
      // setError(errorMessageText); // Optionally display a more prominent error
    } finally {
      setIsLoading(false);
      inputRef.current?.focus(); // Re-focus input after sending
    }
  };

  return (
    <div className="chatbot-container"> {/* Added a container for better context */}
      {!isOpen && (
        <button onClick={toggleChat} className="chatbot-toggle-button" title="Open Chat Assistant">
          <ChatIcon /> Assistant
        </button>
      )}

      {isOpen && (
        <div className="chatbot-window" role="dialog" aria-labelledby="chatbot-header-title">
          <div className="chatbot-header">
            <h3 id="chatbot-header-title">InvoxAI Assistant</h3>
            <button onClick={toggleChat} className="chatbot-close-button" title="Close Chat" aria-label="Close chat window">
              <CloseIcon />
            </button>
          </div>
          <div className="chatbot-messages" aria-live="polite">
            {messages.map((msg) => (
              <div key={msg.id} className={`message-bubble message-${msg.sender} ${msg.isError ? 'message-error-bubble' : ''}`}>
                {/* Basic security: Render text content, not raw HTML from bot */}
                {msg.text.split('\n').map((line, i) => <span key={i}>{line}<br/></span>) /* Handle newlines */}
              </div>
            ))}
            {isLoading && (
              <div className="message-bubble message-bot message-loading" aria-label="Assistant is typing">
                <span>.</span><span>.</span><span>.</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          {/* error state can be used for a general banner, but errors are also shown as bot messages */}
          {/* {error && <p className="chatbot-error-display">{error}</p>} */}
          <form onSubmit={handleSendMessage} className="chatbot-input-form">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={handleInputChange}
              placeholder="Ask about your invoices..."
              disabled={isLoading}
              aria-label="Type your message to the assistant"
            />
            <button type="submit" disabled={isLoading || !inputValue.trim()} aria-label="Send message">
              <SendIcon />
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default Chatbot;