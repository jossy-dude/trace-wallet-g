const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods to renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  // Python bridge
  pythonCommand: (command, data) => ipcRenderer.invoke('python-command', command, data),
  
  // Database operations
  getTransactions: (limit, pendingOnly) => 
    ipcRenderer.invoke('python-command', 'get_transactions', { limit, pending_only: pendingOnly }),
  
  addTransaction: (transaction) => 
    ipcRenderer.invoke('python-command', 'add_transaction', transaction),
  
  updateTransaction: (transaction) => 
    ipcRenderer.invoke('python-command', 'update_transaction', transaction),
  
  deleteTransaction: (id) => 
    ipcRenderer.invoke('python-command', 'delete_transaction', id),
  
  searchTransactions: (query) => 
    ipcRenderer.invoke('python-command', 'search_transactions', query),
  
  // People operations
  getPeople: () => ipcRenderer.invoke('python-command', 'get_people'),
  
  addPerson: (person) => 
    ipcRenderer.invoke('python-command', 'add_person', person),
  
  updatePerson: (person) => 
    ipcRenderer.invoke('python-command', 'update_person', person),
  
  deletePerson: (id) => 
    ipcRenderer.invoke('python-command', 'delete_person', id),
  
  findPersonByAlias: (alias) => 
    ipcRenderer.invoke('python-command', 'find_person_by_alias', alias),
  
  // Parser
  parseTransaction: (rawText) => 
    ipcRenderer.invoke('python-command', 'parse_transaction', rawText),
  
  // Statistics
  getStatistics: () => ipcRenderer.invoke('python-command', 'get_statistics'),
  
  // Import/Export
  exportData: (filepath) => 
    ipcRenderer.invoke('python-command', 'export_data', filepath),
  
  importData: (filepath) => 
    ipcRenderer.invoke('python-command', 'import_data', filepath),
  
  // Platform info
  platform: process.platform
});
