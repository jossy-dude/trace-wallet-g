/**
 * Python Bridge - Utility for communicating with Python sidecar
 * This can be used in the renderer process via the exposed API
 */

class PythonBridge {
  constructor() {
    this.isElectron = window.electronAPI !== undefined;
  }

  async getTransactions(limit = null, pendingOnly = false) {
    if (!this.isElectron) {
      // Fallback to API or local storage in browser mode
      return this._mockGetTransactions(limit, pendingOnly);
    }
    const result = await window.electronAPI.getTransactions(limit, pendingOnly);
    return result.data || [];
  }

  async addTransaction(transaction) {
    if (!this.isElectron) {
      return this._mockAddTransaction(transaction);
    }
    const result = await window.electronAPI.addTransaction(transaction);
    return result.data;
  }

  async updateTransaction(transaction) {
    if (!this.isElectron) {
      return this._mockUpdateTransaction(transaction);
    }
    const result = await window.electronAPI.updateTransaction(transaction);
    return result.data;
  }

  async deleteTransaction(id) {
    if (!this.isElectron) {
      return this._mockDeleteTransaction(id);
    }
    const result = await window.electronAPI.deleteTransaction(id);
    return result.data;
  }

  async searchTransactions(query) {
    if (!this.isElectron) {
      return this._mockSearchTransactions(query);
    }
    const result = await window.electronAPI.searchTransactions(query);
    return result.data || [];
  }

  async getPeople() {
    if (!this.isElectron) {
      return this._mockGetPeople();
    }
    const result = await window.electronAPI.getPeople();
    return result.data || [];
  }

  async addPerson(person) {
    if (!this.isElectron) {
      return this._mockAddPerson(person);
    }
    const result = await window.electronAPI.addPerson(person);
    return result.data;
  }

  async updatePerson(person) {
    if (!this.isElectron) {
      return this._mockUpdatePerson(person);
    }
    const result = await window.electronAPI.updatePerson(person);
    return result.data;
  }

  async deletePerson(id) {
    if (!this.isElectron) {
      return this._mockDeletePerson(id);
    }
    const result = await window.electronAPI.deletePerson(id);
    return result.data;
  }

  async findPersonByAlias(alias) {
    if (!this.isElectron) {
      return this._mockFindPersonByAlias(alias);
    }
    const result = await window.electronAPI.findPersonByAlias(alias);
    return result.data;
  }

  async parseTransaction(rawText) {
    if (!this.isElectron) {
      return this._mockParseTransaction(rawText);
    }
    const result = await window.electronAPI.parseTransaction(rawText);
    return result.data;
  }

  async getStatistics() {
    if (!this.isElectron) {
      return this._mockGetStatistics();
    }
    const result = await window.electronAPI.getStatistics();
    return result.data;
  }

  async exportData(filepath) {
    if (!this.isElectron) {
      return this._mockExportData(filepath);
    }
    const result = await window.electronAPI.exportData(filepath);
    return result.data;
  }

  async importData(filepath) {
    if (!this.isElectron) {
      return this._mockImportData(filepath);
    }
    const result = await window.electronAPI.importData(filepath);
    return result.data;
  }

  // Mock implementations for browser development
  _mockGetTransactions(limit, pendingOnly) {
    const transactions = JSON.parse(localStorage.getItem('transactions') || '[]');
    let result = transactions;
    if (pendingOnly) {
      result = result.filter(t => !t.is_approved);
    }
    if (limit) {
      result = result.slice(0, limit);
    }
    return Promise.resolve(result);
  }

  _mockAddTransaction(transaction) {
    const transactions = JSON.parse(localStorage.getItem('transactions') || '[]');
    const newTx = { ...transaction, id: Date.now() };
    transactions.unshift(newTx);
    localStorage.setItem('transactions', JSON.stringify(transactions));
    return Promise.resolve({ id: newTx.id, status: 'success' });
  }

  _mockUpdateTransaction(transaction) {
    const transactions = JSON.parse(localStorage.getItem('transactions') || '[]');
    const index = transactions.findIndex(t => t.id === transaction.id);
    if (index !== -1) {
      transactions[index] = transaction;
      localStorage.setItem('transactions', JSON.stringify(transactions));
    }
    return Promise.resolve({ success: true });
  }

  _mockDeleteTransaction(id) {
    const transactions = JSON.parse(localStorage.getItem('transactions') || '[]');
    const filtered = transactions.filter(t => t.id !== id);
    localStorage.setItem('transactions', JSON.stringify(filtered));
    return Promise.resolve({ success: true });
  }

  _mockSearchTransactions(query) {
    const transactions = JSON.parse(localStorage.getItem('transactions') || '[]');
    const lowerQuery = query.toLowerCase();
    const result = transactions.filter(t => 
      (t.raw_text && t.raw_text.toLowerCase().includes(lowerQuery)) ||
      (t.sender_alias && t.sender_alias.toLowerCase().includes(lowerQuery)) ||
      (t.category && t.category.toLowerCase().includes(lowerQuery))
    );
    return Promise.resolve(result);
  }

  _mockGetPeople() {
    const people = JSON.parse(localStorage.getItem('people') || '[]');
    return Promise.resolve(people);
  }

  _mockAddPerson(person) {
    const people = JSON.parse(localStorage.getItem('people') || '[]');
    const newPerson = { ...person, id: Date.now() };
    people.push(newPerson);
    localStorage.setItem('people', JSON.stringify(people));
    return Promise.resolve({ id: newPerson.id, status: 'success' });
  }

  _mockUpdatePerson(person) {
    const people = JSON.parse(localStorage.getItem('people') || '[]');
    const index = people.findIndex(p => p.id === person.id);
    if (index !== -1) {
      people[index] = person;
      localStorage.setItem('people', JSON.stringify(people));
    }
    return Promise.resolve({ success: true });
  }

  _mockDeletePerson(id) {
    const people = JSON.parse(localStorage.getItem('people') || '[]');
    const filtered = people.filter(p => p.id !== id);
    localStorage.setItem('people', JSON.stringify(filtered));
    return Promise.resolve({ success: true });
  }

  _mockFindPersonByAlias(alias) {
    const people = JSON.parse(localStorage.getItem('people') || '[]');
    const person = people.find(p => 
      p.aliases && p.aliases.some(a => a.toLowerCase() === alias.toLowerCase())
    );
    return Promise.resolve(person || null);
  }

  _mockParseTransaction(rawText) {
    // Simple regex parsing for demo
    const amountMatch = rawText.match(/ETB\s*([\d,]+\.?\d*)/i);
    const bankMatch = rawText.match(/(CBE|Telebirr|BOA)/i);
    
    return Promise.resolve({
      bank: bankMatch ? bankMatch[1] : 'Other',
      amount: amountMatch ? parseFloat(amountMatch[1].replace(/,/g, '')) : null,
      balance: null,
      fee: null,
      entity_name: null,
      is_valid: !!amountMatch
    });
  }

  _mockGetStatistics() {
    const transactions = JSON.parse(localStorage.getItem('transactions') || '[]');
    const people = JSON.parse(localStorage.getItem('people') || '[]');
    
    const totalIncome = transactions
      .filter(t => t.amount > 0)
      .reduce((sum, t) => sum + (t.amount || 0), 0);
    
    const totalExpense = transactions
      .filter(t => t.amount < 0)
      .reduce((sum, t) => sum + Math.abs(t.amount || 0), 0);
    
    return Promise.resolve({
      total_transactions: transactions.length,
      total_people: people.length,
      pending_count: transactions.filter(t => !t.is_approved).length,
      total_income: totalIncome,
      total_expense: totalExpense,
      database_size: 'Local Storage',
      db_path: 'Browser LocalStorage'
    });
  }

  _mockExportData(filepath) {
    const data = {
      transactions: JSON.parse(localStorage.getItem('transactions') || '[]'),
      people: JSON.parse(localStorage.getItem('people') || '[]'),
      exported_at: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filepath;
    a.click();
    URL.revokeObjectURL(url);
    
    return Promise.resolve({ success: true, path: filepath });
  }

  _mockImportData(filepath) {
    // In browser mode, this would require file input
    return Promise.resolve({ success: true });
  }
}

// Export for use in React components
export const pythonBridge = new PythonBridge();
export default PythonBridge;
