// frontend/src/components/layout/Sidebar.jsx
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Sidebar.css'; 
// Example: Using placeholder icons for now
// You would ideally replace these with actual SVG icons or an icon library
const IconDashboard = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>;
const IconUpload = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>;
const IconInvoices = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>;
const IconReports = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg>;


const menuItems = [
  { path: '/', label: 'Home', icon: <IconDashboard /> }, // "Home" as per Invo.
  { path: '/invoices', label: 'Invoices', icon: <IconInvoices /> }, // Our "View Invoices"
  // Add Clients, Products, Messages, Settings, Help if you build those pages
  // For InvoxAI, let's keep our existing relevant items:
  { path: '/upload', label: 'Upload Invoice', icon: <IconUpload /> },
  { path: '/reports', label: 'Reports', icon: <IconReports /> },
];

const Sidebar = () => {
  const location = useLocation();

  return (
    <aside className="app-sidebar-invo"> {/* Specific class for this layout style */}
      <div className="sidebar-header-invo">
        {/* Replace with your actual logo component or SVG */}
        <svg className="sidebar-logo-invo" width="32" height="32" viewBox="0 0 24 24" fill="var(--color-primary-accent)">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path>
        </svg>
        <span className="sidebar-brand-name-invo">Invox.AI</span>
      </div>
      <nav className="sidebar-navigation-invo">
        <p className="menu-group-title-invo">MENU</p>
        <ul className="sidebar-menu-list-invo">
          {menuItems.map((item) => (
            <li key={item.path}>
              <Link
                to={item.path}
                className={`sidebar-menu-item-invo ${
                  (item.path === '/' && location.pathname === '/') ||
                  (item.path !== '/' && location.pathname.startsWith(item.path))
                    ? 'active'
                    : ''
                }`}
              >
                <span className="sidebar-menu-icon-invo">{item.icon}</span>
                <span className="sidebar-menu-label-invo">{item.label}</span>
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
};

export default Sidebar;
