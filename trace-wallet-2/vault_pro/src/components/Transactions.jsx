import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Filter, 
  Plus, 
  CheckCircle, 
  XCircle, 
  Edit2, 
  Trash2,
  Download,
  Upload,
  MoreVertical,
  Banknote,
  Smartphone
} from 'lucide-react';

const Transactions = () => {
  const [transactions, setTransactions] = useState([]);
  const [filteredTransactions, setFilteredTransactions] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Form state
  const [formData, setFormData] = useState({
    rawText: '',
    amount: '',
    balance: '',
    fee: '',
    senderAlias: '',
    category: 'CBE',
    date: new Date().toISOString().split('T')[0],
    isApproved: false
  });

  const fetchTransactions = async () => {
    setIsLoading(true);
    try {
      if (window.electronAPI) {
        const response = await window.electronAPI.getTransactions();
        if (response && response.success) {
          setTransactions(response.data || []);
        }
      } else {
        // Fallback for development if electronAPI is not available
        console.warn('Electron API not found, using sample data');
        const sampleTransactions = [
          {
            id: 1,
            rawText: 'Your CBE account debited with ETB 5,000. Current balance is ETB 45,678.90',
            amount: 5000,
            balance: 45678.90,
            fee: 25,
            senderAlias: 'John Doe',
            category: 'CBE',
            date: '2024-01-15',
            isApproved: true,
            dateAdded: '2024-01-15T10:30:00'
          }
        ];
        setTransactions(sampleTransactions);
      }
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, []);

  useEffect(() => {
    if (!Array.isArray(transactions)) {
      setFilteredTransactions([]);
      return;
    }

    let filtered = [...transactions];
    
    if (searchTerm) {
      const lowerSearch = searchTerm.toLowerCase();
      filtered = filtered.filter(tx => 
        (tx.rawText || '').toLowerCase().includes(lowerSearch) ||
        (tx.senderAlias || '').toLowerCase().includes(lowerSearch) ||
        (tx.category || '').toLowerCase().includes(lowerSearch)
      );
    }
    
    if (filterStatus !== 'all') {
      if (filterStatus === 'approved') {
        filtered = filtered.filter(tx => tx.isApproved);
      } else if (filterStatus === 'pending') {
        filtered = filtered.filter(tx => !tx.isApproved);
      } else {
        filtered = filtered.filter(tx => tx.category === filterStatus);
      }
    }
    
    setFilteredTransactions(filtered);
  }, [searchTerm, filterStatus, transactions]);

  const validateTransaction = (data) => {
    const errors = [];
    if (!data.amount || isNaN(parseFloat(data.amount))) {
      errors.push('Valid amount is required');
    }
    if (!data.date) {
      errors.push('Date is required');
    }
    return errors;
  };

  const handleAddTransaction = async () => {
    const validationErrors = validateTransaction(formData);
    if (validationErrors.length > 0) {
      alert('Please fix the following errors:\n' + validationErrors.join('\n'));
      return;
    }

    const payload = {
      raw_text: formData.rawText.trim(),
      amount: parseFloat(formData.amount),
      balance: formData.balance ? parseFloat(formData.balance) : null,
      fee: formData.fee ? parseFloat(formData.fee) : null,
      date: formData.date,
      sender_alias: formData.senderAlias.trim() || null,
      category: formData.category,
      is_approved: formData.isApproved,
    };
    
    try {
      if (window.electronAPI) {
        const response = await window.electronAPI.addTransaction(payload);
        if (response && response.success) {
          fetchTransactions();
          setShowAddModal(false);
          resetForm();
        } else {
          alert('Failed to add transaction: ' + (response?.error || 'Unknown error'));
        }
      } else {
        const newTransaction = {
          id: Date.now(),
          ...payload,
          dateAdded: new Date().toISOString()
        };
        setTransactions([newTransaction, ...transactions]);
        setShowAddModal(false);
        resetForm();
      }
    } catch (error) {
      console.error('Error adding transaction:', error);
      alert('Error adding transaction: ' + error.message);
    }
  };

  const resetForm = () => {
    setFormData({
      rawText: '',
      amount: '',
      balance: '',
      fee: '',
      senderAlias: '',
      category: 'CBE',
      date: new Date().toISOString().split('T')[0],
      isApproved: false
    });
  };

  const handleUpdateTransaction = async () => {
    if (!editingTransaction || !editingTransaction.id) {
      alert('Invalid transaction data');
      return;
    }

    try {
      // Normalize field names for backend
      const payload = {
        ...editingTransaction,
        raw_text: editingTransaction.rawText || editingTransaction.raw_text,
        sender_alias: editingTransaction.senderAlias || editingTransaction.sender_alias,
        is_approved: editingTransaction.isApproved ?? editingTransaction.is_approved ?? false,
      };

      if (window.electronAPI) {
        const response = await window.electronAPI.updateTransaction(payload);
        if (response && response.success) {
          fetchTransactions();
          setEditingTransaction(null);
        } else {
          alert('Failed to update transaction: ' + (response?.error || 'Unknown error'));
        }
      } else {
        setTransactions(transactions.map(tx => 
          tx.id === editingTransaction.id ? { ...editingTransaction } : tx
        ));
        setEditingTransaction(null);
      }
    } catch (error) {
      console.error('Error updating transaction:', error);
      alert('Error updating transaction: ' + error.message);
    }
  };

  const handleDeleteTransaction = async (id) => {
    if (window.confirm('Are you sure you want to delete this transaction?')) {
      try {
        if (window.electronAPI) {
          const response = await window.electronAPI.deleteTransaction(id);
          if (response && response.success) {
            fetchTransactions();
          } else {
            alert('Failed to delete transaction: ' + (response?.error || 'Unknown error'));
          }
        } else {
          setTransactions(transactions.filter(tx => tx.id !== id));
        }
      } catch (error) {
        console.error('Error deleting transaction:', error);
        alert('Error deleting transaction: ' + error.message);
      }
    }
  };

  const handleApproveTransaction = async (id) => {
    const txToApprove = transactions.find(t => t.id === id);
    if (!txToApprove) return;

    // Normalize for backend
    const updatedTx = { 
      ...txToApprove, 
      is_approved: true,
      raw_text: txToApprove.rawText || txToApprove.raw_text || '',
      sender_alias: txToApprove.senderAlias || txToApprove.sender_alias || null
    };
    
    try {
      if (window.electronAPI) {
        const response = await window.electronAPI.updateTransaction(updatedTx);
        if (response && response.success) {
          fetchTransactions();
        } else {
          alert('Failed to approve transaction: ' + (response?.error || 'Unknown error'));
        }
      } else {
        setTransactions(transactions.map(tx => 
          tx.id === id ? { ...tx, isApproved: true } : tx
        ));
      }
    } catch (error) {
      console.error('Error approving transaction:', error);
      alert('Error approving transaction: ' + error.message);
    }
  };

  const getBankBadgeClass = (category) => {
    switch(category) {
      case 'CBE': return 'badge-cbe';
      case 'Telebirr': return 'badge-telebirr';
      case 'BOA': return 'badge-boa';
      default: return 'bg-slate-500/20 text-slate-400 border border-slate-500/30';
    }
  };

  const formatCurrency = (amount) => {
    if (amount === null || amount === undefined || isNaN(amount)) return '0.00';
    return amount.toLocaleString('en-US', { minimumFractionDigits: 2 });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <h2 className="text-2xl font-bold text-slate-100">Transactions</h2>
        <div className="flex gap-3">
          <button className="btn-secondary flex items-center gap-2">
            <Download className="w-4 h-4" />
            Export
          </button>
          <button className="btn-secondary flex items-center gap-2">
            <Upload className="w-4 h-4" />
            Import
          </button>
          <button 
            onClick={() => setShowAddModal(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Transaction
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-card p-4 flex flex-col md:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
          <input
            type="text"
            placeholder="Search transactions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input-field pl-10"
          />
        </div>
        <div className="flex gap-3">
          <select 
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="input-field w-40"
          >
            <option value="all">All Status</option>
            <option value="approved">Approved</option>
            <option value="pending">Pending</option>
            <option value="CBE">CBE</option>
            <option value="Telebirr">Telebirr</option>
            <option value="BOA">BOA</option>
          </select>
          <button className="btn-secondary flex items-center gap-2">
            <Filter className="w-4 h-4" />
            More Filters
          </button>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-dark-800/50">
              <tr>
                <th className="text-left px-6 py-4 text-sm font-semibold text-slate-400">Date</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-slate-400">Bank</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-slate-400">Description</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-slate-400">Amount</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-slate-400">Balance</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-slate-400">Status</th>
                <th className="text-left px-6 py-4 text-sm font-semibold text-slate-400">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-700">
              {filteredTransactions.map((tx) => (
                <tr key={tx.id} className="hover:bg-dark-800/30 transition-colors">
                  <td className="px-6 py-4 text-slate-300">{tx.date}</td>
                  <td className="px-6 py-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getBankBadgeClass(tx.category)}`}>
                      {tx.category}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="max-w-xs">
                      <p className="text-slate-300 truncate">{tx.rawText || tx.raw_text}</p>
                      <p className="text-sm text-slate-500">{tx.senderAlias || tx.sender_alias}</p>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`font-semibold ${tx.amount > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      ETB {formatCurrency(tx.amount)}
                    </span>
                    {tx.fee > 0 && (
                      <p className="text-xs text-slate-500">Fee: ETB {formatCurrency(tx.fee)}</p>
                    )}
                  </td>
                  <td className="px-6 py-4 text-slate-300">
                    {tx.balance ? `ETB ${formatCurrency(tx.balance)}` : '-'}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      (tx.isApproved || tx.is_approved) ? 'status-approved' : 'status-pending'
                    }`}>
                      {(tx.isApproved || tx.is_approved) ? 'Approved' : 'Pending'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {!(tx.isApproved || tx.is_approved) && (
                        <button 
                          onClick={() => handleApproveTransaction(tx.id)}
                          className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors"
                          title="Approve"
                        >
                          <CheckCircle className="w-4 h-4" />
                        </button>
                      )}
                      <button 
                        onClick={() => setEditingTransaction(tx)}
                        className="p-2 rounded-lg bg-vault-500/20 text-vault-400 hover:bg-vault-500/30 transition-colors"
                        title="Edit"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button 
                        onClick={() => handleDeleteTransaction(tx.id)}
                        className="p-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredTransactions.length === 0 && (
          <div className="text-center py-12">
            <Banknote className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-500">No transactions found</p>
          </div>
        )}
      </div>

      {/* Add Transaction Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="glass-card w-full max-w-2xl max-h-[90vh] overflow-y-auto m-4">
            <div className="p-6 border-b border-dark-700">
              <h3 className="text-xl font-bold text-slate-100">Add Transaction</h3>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Raw SMS/Text</label>
                <textarea
                  value={formData.rawText}
                  onChange={(e) => setFormData({...formData, rawText: e.target.value})}
                  className="input-field h-24 resize-none"
                  placeholder="Paste the transaction message here..."
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">Amount (ETB)</label>
                  <input
                    type="number"
                    value={formData.amount}
                    onChange={(e) => setFormData({...formData, amount: e.target.value})}
                    className="input-field"
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">Balance (ETB)</label>
                  <input
                    type="number"
                    value={formData.balance}
                    onChange={(e) => setFormData({...formData, balance: e.target.value})}
                    className="input-field"
                    placeholder="0.00"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">Fee (ETB)</label>
                  <input
                    type="number"
                    value={formData.fee}
                    onChange={(e) => setFormData({...formData, fee: e.target.value})}
                    className="input-field"
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">Sender/Recipient</label>
                  <input
                    type="text"
                    value={formData.senderAlias}
                    onChange={(e) => setFormData({...formData, senderAlias: e.target.value})}
                    className="input-field"
                    placeholder="Name"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">Bank</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({...formData, category: e.target.value})}
                    className="input-field"
                  >
                    <option value="CBE">CBE</option>
                    <option value="Telebirr">Telebirr</option>
                    <option value="BOA">BOA</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">Date</label>
                  <input
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData({...formData, date: e.target.value})}
                    className="input-field"
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="isApproved"
                  checked={formData.isApproved}
                  onChange={(e) => setFormData({...formData, isApproved: e.target.checked})}
                  className="w-4 h-4 rounded border-dark-600 bg-dark-800 text-vault-500 focus:ring-vault-500"
                />
                <label htmlFor="isApproved" className="text-slate-300">Mark as approved</label>
              </div>
            </div>
            <div className="p-6 border-t border-dark-700 flex justify-end gap-3">
              <button 
                onClick={() => setShowAddModal(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button 
                onClick={handleAddTransaction}
                className="btn-primary"
              >
                Add Transaction
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Transaction Modal */}
      {editingTransaction && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="glass-card w-full max-w-2xl max-h-[90vh] overflow-y-auto m-4">
            <div className="p-6 border-b border-dark-700">
              <h3 className="text-xl font-bold text-slate-100">Edit Transaction</h3>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Raw SMS/Text</label>
                <textarea
                  value={editingTransaction.rawText}
                  onChange={(e) => setEditingTransaction({...editingTransaction, rawText: e.target.value})}
                  className="input-field h-24 resize-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">Amount (ETB)</label>
                  <input
                    type="number"
                    value={editingTransaction.amount}
                    onChange={(e) => setEditingTransaction({...editingTransaction, amount: parseFloat(e.target.value)})}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">Balance (ETB)</label>
                  <input
                    type="number"
                    value={editingTransaction.balance || ''}
                    onChange={(e) => setEditingTransaction({...editingTransaction, balance: parseFloat(e.target.value) || null})}
                    className="input-field"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">Fee (ETB)</label>
                  <input
                    type="number"
                    value={editingTransaction.fee || ''}
                    onChange={(e) => setEditingTransaction({...editingTransaction, fee: parseFloat(e.target.value) || null})}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">Sender/Recipient</label>
                  <input
                    type="text"
                    value={editingTransaction.senderAlias}
                    onChange={(e) => setEditingTransaction({...editingTransaction, senderAlias: e.target.value})}
                    className="input-field"
                  />
                </div>
              </div>
            </div>
            <div className="p-6 border-t border-dark-700 flex justify-end gap-3">
              <button 
                onClick={() => setEditingTransaction(null)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button 
                onClick={handleUpdateTransaction}
                className="btn-primary"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Transactions;
