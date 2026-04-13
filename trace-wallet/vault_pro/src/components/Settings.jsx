import React, { useState, useEffect } from 'react';
import { 
  Settings as SettingsIcon, 
  Database, 
  Bell, 
  Shield, 
  Palette, 
  Save,
  RefreshCw,
  Download,
  Upload,
  Trash2,
  AlertTriangle
} from 'lucide-react';

const Settings = () => {
  const [settings, setSettings] = useState({
    notifications: {
      syncComplete: true,
      newTransaction: true,
      pendingReview: true,
      monthlyReport: false
    },
    security: {
      requireApproval: true,
      autoLock: 15,
      encryptData: true
    },
    display: {
      theme: 'dark',
      language: 'en',
      dateFormat: 'YYYY-MM-DD',
      currency: 'ETB'
    },
    database: {
      autoBackup: true,
      backupInterval: 7
    }
  });

  const [storageInfo, setStorageInfo] = useState({
    totalTransactions: 156,
    totalPeople: 24,
    databaseSize: '2.4 MB',
    lastBackup: '2024-01-14 08:30'
  });

  const handleSave = () => {
    alert('Settings saved successfully!');
  };

  const handleClearData = () => {
    if (confirm('WARNING: This will delete all your data. Are you sure?')) {
      alert('Data cleared. Please restart the application.');
    }
  };

  const handleExportData = () => {
    const data = JSON.stringify({ settings, storageInfo }, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `vault-backup-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Settings</h2>
          <p className="text-slate-500 mt-1">Configure your Vault Pro preferences</p>
        </div>
        <button 
          onClick={handleSave}
          className="btn-primary flex items-center gap-2"
        >
          <Save className="w-4 h-4" />
          Save Changes
        </button>
      </div>

      {/* Settings Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Notifications */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-vault-500/20 flex items-center justify-center">
              <Bell className="w-5 h-5 text-vault-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-100">Notifications</h3>
          </div>
          <div className="space-y-4">
            {Object.entries(settings.notifications).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-slate-300 capitalize">
                  {key.replace(/([A-Z])/g, ' $1').trim()}
                </span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={value}
                    onChange={(e) => setSettings({
                      ...settings,
                      notifications: { ...settings.notifications, [key]: e.target.checked }
                    })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-dark-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vault-500"></div>
                </label>
              </div>
            ))}
          </div>
        </div>

        {/* Security */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
              <Shield className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-100">Security</h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-slate-300">Require approval for new transactions</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.security.requireApproval}
                  onChange={(e) => setSettings({
                    ...settings,
                    security: { ...settings.security, requireApproval: e.target.checked }
                  })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-dark-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vault-500"></div>
              </label>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-300">Encrypt sensitive data</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.security.encryptData}
                  onChange={(e) => setSettings({
                    ...settings,
                    security: { ...settings.security, encryptData: e.target.checked }
                  })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-dark-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vault-500"></div>
              </label>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">
                Auto-lock after (minutes)
              </label>
              <select
                value={settings.security.autoLock}
                onChange={(e) => setSettings({
                  ...settings,
                  security: { ...settings.security, autoLock: parseInt(e.target.value) }
                })}
                className="input-field w-32"
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={15}>15</option>
                <option value={30}>30</option>
                <option value={60}>60</option>
              </select>
            </div>
          </div>
        </div>

        {/* Display */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
              <Palette className="w-5 h-5 text-purple-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-100">Display</h3>
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Theme</label>
              <select
                value={settings.display.theme}
                onChange={(e) => setSettings({
                  ...settings,
                  display: { ...settings.display, theme: e.target.value }
                })}
                className="input-field"
              >
                <option value="dark">Dark</option>
                <option value="light">Light</option>
                <option value="system">System</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Currency</label>
              <select
                value={settings.display.currency}
                onChange={(e) => setSettings({
                  ...settings,
                  display: { ...settings.display, currency: e.target.value }
                })}
                className="input-field"
              >
                <option value="ETB">ETB (Ethiopian Birr)</option>
                <option value="USD">USD (US Dollar)</option>
                <option value="EUR">EUR (Euro)</option>
                <option value="GBP">GBP (British Pound)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Date Format</label>
              <select
                value={settings.display.dateFormat}
                onChange={(e) => setSettings({
                  ...settings,
                  display: { ...settings.display, dateFormat: e.target.value }
                })}
                className="input-field"
              >
                <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                <option value="MM/DD/YYYY">MM/DD/YYYY</option>
              </select>
            </div>
          </div>
        </div>

        {/* Database */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center">
              <Database className="w-5 h-5 text-blue-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-100">Database</h3>
          </div>
          
          <div className="space-y-4 mb-6">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Total Transactions</span>
              <span className="text-slate-200 font-medium">{storageInfo.totalTransactions}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Total People</span>
              <span className="text-slate-200 font-medium">{storageInfo.totalPeople}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Database Size</span>
              <span className="text-slate-200 font-medium">{storageInfo.databaseSize}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Last Backup</span>
              <span className="text-slate-200 font-medium">{storageInfo.lastBackup}</span>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-slate-300">Auto-backup</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.database.autoBackup}
                  onChange={(e) => setSettings({
                    ...settings,
                    database: { ...settings.database, autoBackup: e.target.checked }
                  })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-dark-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vault-500"></div>
              </label>
            </div>
            {settings.database.autoBackup && (
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">
                  Backup every (days)
                </label>
                <select
                  value={settings.database.backupInterval}
                  onChange={(e) => setSettings({
                    ...settings,
                    database: { ...settings.database, backupInterval: parseInt(e.target.value) }
                  })}
                  className="input-field w-32"
                >
                  <option value={1}>1</option>
                  <option value={3}>3</option>
                  <option value={7}>7</option>
                  <option value={14}>14</option>
                  <option value={30}>30</option>
                </select>
              </div>
            )}
          </div>

          <div className="flex gap-3 mt-6 pt-6 border-t border-dark-700">
            <button 
              onClick={handleExportData}
              className="flex-1 btn-secondary flex items-center justify-center gap-2"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
            <button className="flex-1 btn-secondary flex items-center justify-center gap-2">
              <Upload className="w-4 h-4" />
              Import
            </button>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="glass-card p-6 border border-red-500/30">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-red-400" />
          </div>
          <h3 className="text-lg font-semibold text-red-400">Danger Zone</h3>
        </div>
        <p className="text-slate-500 mb-4">
          These actions are irreversible. Please be certain before proceeding.
        </p>
        <button 
          onClick={handleClearData}
          className="btn-danger flex items-center gap-2"
        >
          <Trash2 className="w-4 h-4" />
          Clear All Data
        </button>
      </div>
    </div>
  );
};

export default Settings;
