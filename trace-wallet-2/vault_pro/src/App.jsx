import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Wallet, 
  Users, 
  Settings as SettingsIcon, 
  Smartphone,
  Bell,
  Menu,
  X
} from 'lucide-react';

// Components
import Dashboard from './components/Dashboard';
import Transactions from './components/Transactions';
import People from './components/People';
import Sync from './components/Sync';
import Settings from './components/Settings';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [notifications, setNotifications] = useState([]);

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/transactions', icon: Wallet, label: 'Transactions' },
    { path: '/people', icon: Users, label: 'People' },
    { path: '/sync', icon: Smartphone, label: 'Sync' },
    { path: '/settings', icon: SettingsIcon, label: 'Settings' },
  ];

  return (
    <Router>
      <div className="flex h-screen bg-dark-900">
        {/* Sidebar */}
        <aside 
          className={`${sidebarOpen ? 'w-64' : 'w-20'} glass transition-all duration-300 flex flex-col`}
        >
          {/* Logo */}
          <div className="p-6 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-vault-400 to-vault-600 flex items-center justify-center animate-pulse-glow">
              <Wallet className="w-6 h-6 text-white" />
            </div>
            {sidebarOpen && (
              <span className="text-xl font-bold bg-gradient-to-r from-vault-400 to-vault-300 bg-clip-text text-transparent">
                Vault Pro
              </span>
            )}
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-4 space-y-2">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `
                  flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200
                  ${isActive 
                    ? 'bg-vault-500/20 text-vault-400 border border-vault-500/30' 
                    : 'text-slate-400 hover:bg-dark-800 hover:text-slate-200'}
                `}
              >
                <item.icon className="w-5 h-5" />
                {sidebarOpen && <span className="font-medium">{item.label}</span>}
              </NavLink>
            ))}
          </nav>

          {/* Toggle Button */}
          <div className="p-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="w-full flex items-center justify-center p-3 rounded-xl bg-dark-800 hover:bg-dark-700 transition-colors"
            >
              {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <header className="glass px-6 py-4 flex items-center justify-between">
            <h1 className="text-2xl font-bold text-slate-100">
              Financial Command Center
            </h1>
            <div className="flex items-center gap-4">
              <button className="relative p-2 rounded-xl bg-dark-800 hover:bg-dark-700 transition-colors">
                <Bell className="w-5 h-5 text-slate-400" />
                {notifications.length > 0 && (
                  <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
                )}
              </button>
              <div className="flex items-center gap-3 px-4 py-2 rounded-xl bg-dark-800">
                <div className="w-8 h-8 rounded-full bg-vault-500/30 flex items-center justify-center">
                  <span className="text-sm font-bold text-vault-400">VP</span>
                </div>
                <span className="text-sm font-medium text-slate-300">Admin</span>
              </div>
            </div>
          </header>

          {/* Page Content */}
          <div className="flex-1 overflow-auto p-6">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/transactions" element={<Transactions />} />
              <Route path="/people" element={<People />} />
              <Route path="/sync" element={<Sync />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  );
}

export default App;
