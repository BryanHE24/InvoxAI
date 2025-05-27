// frontend/src/components/layout/Layout.jsx
import React from 'react';
import Navbar from './Navbar.jsx'; // This is the top bar inside the content area
import Sidebar from './Sidebar.jsx';
import './Layout.css';

const Layout = ({ children }) => {
  return (
    <div className="app-layout-invo"> {/* Main flex container */}
      <Sidebar /> {/* Fixed Sidebar */}
      <div className="app-content-area-invo"> {/* Area to the right of Sidebar */}
        <Navbar /> {/* Top bar within the content area */}
        <main className="main-page-content-invo"> {/* Actual scrollable page content */}
          {children}
        </main>
      </div>
    </div>
  );
};
export default Layout;