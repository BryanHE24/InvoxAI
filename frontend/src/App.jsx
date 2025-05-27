// frontend/src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import UploadPage from './pages/UploadPage.jsx';
import InvoicesPage from './pages/InvoicesPage.jsx';
import ViewInvoicePage from './pages/ViewInvoicePage.jsx';
import ReportsPage from './pages/ReportsPage.jsx'; // <-- IMPORT NEW PAGE
import NotFoundPage from './pages/NotFoundPage.jsx';
import Chatbot from './components/chatbot/Chatbot.jsx';
import './App.css';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/invoices" element={<InvoicesPage />} />
          <Route path="/invoices/:id" element={<ViewInvoicePage />} />
          <Route path="/reports" element={<ReportsPage />} /> {/* <-- ADD NEW ROUTE */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Layout>
      <Chatbot />
    </Router>
  );
}

export default App;