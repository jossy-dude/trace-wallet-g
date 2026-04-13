import React, { useState, useEffect } from 'react';
import { 
  Smartphone, 
  Laptop, 
  RefreshCw, 
  CheckCircle, 
  XCircle, 
  Clock,
  Wifi,
  WifiOff,
  Server,
  Mobile,
  Link,
  Unlink,
  Send,
  Download,
  AlertCircle
} from 'lucide-react';

const Sync = () => {
  const [serverStatus, setServerStatus] = useState('offline');
  const [connectedDevices, setConnectedDevices] = useState([]);
  const [syncHistory, setSyncHistory] = useState([]);
  const [targetIp, setTargetIp] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    // Simulate server status
    setServerStatus('online');
    
    setConnectedDevices([
      { id: 'MOBILE_001', name: 'Yohannes Phone', type: 'mobile', status: 'trusted', lastSync: '2024-01-15 14:30' },
    ]);

    setSyncHistory([
      { id: 1, device: 'Yohannes Phone', transactions: 12, status: 'success', timestamp: '2024-01-15 14:30' },
      { id: 2, device: 'Yohannes Phone', transactions: 8, status: 'success', timestamp: '2024-01-14 09:15' },
      { id: 3, device: 'Yohannes Phone', transactions: 0, status: 'failed', timestamp: '2024-01-13 18:45', error: 'Connection timeout' },
    ]);
  }, []);

  const handleSync = async () => {
    if (!targetIp) {
      alert('Please enter target IP address');
      return;
    }
    
    setIsSyncing(true);
    addLog(`Starting sync to ${targetIp}...`);
    
    // Simulate sync process
    setTimeout(() => {
      setIsSyncing(false);
      addLog(`Sync completed. 12 transactions synced.`);
      setSyncHistory([
        { id: Date.now(), device: targetIp, transactions: 12, status: 'success', timestamp: new Date().toLocaleString() },
        ...syncHistory
      ]);
    }, 2000);
  };

  const addLog = (message) => {
    setLogs(prev => [...prev, { timestamp: new Date().toLocaleTimeString(), message }]);
  };

  const handlePairDevice = () => {
    addLog('Scanning for devices...');
    setTimeout(() => {
      addLog('Found device: Android Phone (192.168.1.105)');
    }, 1500);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Sync & Connection</h2>
        <p className="text-slate-500 mt-1">Manage connections between desktop and mobile devices</p>
      </div>

      {/* Server Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                serverStatus === 'online' ? 'bg-emerald-500/20' : 'bg-red-500/20'
              }`}>
                <Server className={`w-6 h-6 ${
                  serverStatus === 'online' ? 'text-emerald-400' : 'text-red-400'
                }`} />
              </div>
              <div>
                <p className="text-sm text-slate-400">Server Status</p>
                <p className={`font-semibold ${
                  serverStatus === 'online' ? 'text-emerald-400' : 'text-red-400'
                }`}>
                  {serverStatus === 'online' ? 'Online' : 'Offline'}
                </p>
              </div>
            </div>
            <div className={`w-3 h-3 rounded-full ${
              serverStatus === 'online' ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'
            }`}></div>
          </div>
          <p className="text-sm text-slate-500">Port: 8080</p>
          <p className="text-sm text-slate-500">IP: 192.168.1.100</p>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-vault-500/20 flex items-center justify-center">
                <Mobile className="w-6 h-6 text-vault-400" />
              </div>
              <div>
                <p className="text-sm text-slate-400">Connected Devices</p>
                <p className="font-semibold text-slate-200">{connectedDevices.length}</p>
              </div>
            </div>
          </div>
          <button 
            onClick={handlePairDevice}
            className="w-full btn-primary flex items-center justify-center gap-2"
          >
            <Link className="w-4 h-4" />
            Pair New Device
          </button>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center">
                <RefreshCw className={`w-6 h-6 text-blue-400 ${isSyncing ? 'animate-spin' : ''}`} />
              </div>
              <div>
                <p className="text-sm text-slate-400">Last Sync</p>
                <p className="font-semibold text-slate-200">2 hours ago</p>
              </div>
            </div>
          </div>
          <p className="text-sm text-slate-500">12 transactions synced</p>
        </div>
      </div>

      {/* Connected Devices */}
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">Connected Devices</h3>
        {connectedDevices.length > 0 ? (
          <div className="space-y-3">
            {connectedDevices.map((device) => (
              <div key={device.id} className="flex items-center justify-between p-4 bg-dark-800/50 rounded-xl">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-vault-500/20 flex items-center justify-center">
                    <Smartphone className="w-5 h-5 text-vault-400" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-200">{device.name}</p>
                    <p className="text-sm text-slate-500">{device.id}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      device.status === 'trusted' ? 'status-approved' : 'status-pending'
                    }`}>
                      {device.status}
                    </span>
                    <p className="text-xs text-slate-500 mt-1">Last sync: {device.lastSync}</p>
                  </div>
                  <button className="p-2 rounded-lg hover:bg-red-500/20 transition-colors">
                    <Unlink className="w-4 h-4 text-red-400" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <Smartphone className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-500">No devices connected</p>
            <button 
              onClick={handlePairDevice}
              className="mt-4 text-vault-400 hover:text-vault-300 text-sm font-medium"
            >
              Pair a device
            </button>
          </div>
        )}
      </div>

      {/* Manual Sync */}
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">Manual Sync</h3>
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-slate-400 mb-2">Target IP Address</label>
            <div className="relative">
              <Wifi className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
              <input
                type="text"
                value={targetIp}
                onChange={(e) => setTargetIp(e.target.value)}
                placeholder="192.168.1.100"
                className="input-field pl-10"
              />
            </div>
          </div>
          <div className="flex items-end">
            <button 
              onClick={handleSync}
              disabled={isSyncing}
              className="btn-primary flex items-center gap-2 disabled:opacity-50"
            >
              {isSyncing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Syncing...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Sync Now
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Sync History */}
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">Sync History</h3>
        <div className="space-y-3">
          {syncHistory.map((sync) => (
            <div key={sync.id} className="flex items-center justify-between p-4 bg-dark-800/50 rounded-xl">
              <div className="flex items-center gap-4">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                  sync.status === 'success' ? 'bg-emerald-500/20' : 'bg-red-500/20'
                }`}>
                  {sync.status === 'success' ? (
                    <CheckCircle className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-400" />
                  )}
                </div>
                <div>
                  <p className="font-medium text-slate-200">{sync.device}</p>
                  <p className="text-sm text-slate-500">{sync.transactions} transactions</p>
                </div>
              </div>
              <div className="text-right">
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  sync.status === 'success' ? 'status-approved' : 'status-review'
                }`}>
                  {sync.status}
                </span>
                <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {sync.timestamp}
                </p>
                {sync.error && (
                  <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    {sync.error}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Activity Log */}
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">Activity Log</h3>
        <div className="bg-dark-900 rounded-xl p-4 h-48 overflow-y-auto font-mono text-sm">
          {logs.length > 0 ? (
            logs.map((log, idx) => (
              <div key={idx} className="flex gap-3 text-slate-400 mb-1">
                <span className="text-vault-500">[{log.timestamp}]</span>
                <span>{log.message}</span>
              </div>
            ))
          ) : (
            <p className="text-slate-600 italic">No activity yet...</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default Sync;
