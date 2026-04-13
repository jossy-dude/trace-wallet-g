import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Plus, 
  Edit2, 
  Trash2, 
  Search,
  Tag,
  UserCircle,
  Wallet,
  History
} from 'lucide-react';

const People = () => {
  const [people, setPeople] = useState([]);
  const [filteredPeople, setFilteredPeople] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingPerson, setEditingPerson] = useState(null);
  const [selectedPerson, setSelectedPerson] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const [formData, setFormData] = useState({
    name: '',
    aliases: '',
    monthlyFee: 0
  });

  const fetchPeople = async () => {
    setIsLoading(true);
    try {
      if (window.electronAPI) {
        const response = await window.electronAPI.getPeople();
        if (response && response.success) {
          // Normalize monthly_fee to monthlyFee for frontend consistency
          const normalizedPeople = (response.data || []).map(p => ({
            ...p,
            monthlyFee: p.monthly_fee ?? p.monthlyFee ?? 0,
            totalTransactions: p.total_transactions ?? p.totalTransactions ?? 0,
            totalAmount: p.total_amount ?? p.totalAmount ?? 0
          }));
          setPeople(normalizedPeople);
        }
      } else {
        const samplePeople = [
          {
            id: 1,
            name: 'John Doe',
            aliases: ['John', 'JD', 'John D'],
            monthlyFee: 500,
            totalTransactions: 12,
            totalAmount: 15000
          }
        ];
        setPeople(samplePeople);
      }
    } catch (error) {
      console.error('Failed to fetch people:', error);
      alert('Failed to load people data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPeople();
  }, []);

  useEffect(() => {
    if (!Array.isArray(people)) {
      setFilteredPeople([]);
      return;
    }

    if (searchTerm) {
      const lowerSearch = searchTerm.toLowerCase();
      setFilteredPeople(people.filter(p => 
        (p.name || '').toLowerCase().includes(lowerSearch) ||
        (p.aliases || []).some(a => (a || '').toLowerCase().includes(lowerSearch))
      ));
    } else {
      setFilteredPeople(people);
    }
  }, [searchTerm, people]);

  const handleAddPerson = async () => {
    const payload = {
      name: formData.name,
      aliases: formData.aliases.split(',').map(a => a.trim()).filter(a => a),
      monthly_fee: parseFloat(formData.monthlyFee) || 0
    };

    if (window.electronAPI) {
      const response = await window.electronAPI.addPerson(payload);
      if (response && response.success) {
        fetchPeople();
        setShowAddModal(false);
        setFormData({ name: '', aliases: '', monthlyFee: 0 });
      }
    } else {
      const newPerson = {
        id: Date.now(),
        ...payload,
        monthlyFee: payload.monthly_fee,
        totalTransactions: 0,
        totalAmount: 0
      };
      setPeople([...people, newPerson]);
      setShowAddModal(false);
      setFormData({ name: '', aliases: '', monthlyFee: 0 });
    }
  };

  const handleUpdatePerson = async () => {
    if (window.electronAPI) {
      const response = await window.electronAPI.updatePerson(editingPerson);
      if (response && response.success) {
        fetchPeople();
        setEditingPerson(null);
      }
    } else {
      setPeople(people.map(p => 
        p.id === editingPerson.id ? editingPerson : p
      ));
      setEditingPerson(null);
    }
  };

  const handleDeletePerson = async (id) => {
    if (window.confirm('Are you sure you want to delete this person?')) {
      if (window.electronAPI) {
        const response = await window.electronAPI.deletePerson(id);
        if (response && response.success) {
          fetchPeople();
        }
      } else {
        setPeople(people.filter(p => p.id !== id));
      }
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">People Management</h2>
          <p className="text-slate-500 mt-1">Manage contacts and their aliases for transaction categorization</p>
        </div>
        <button 
          onClick={() => setShowAddModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Add Person
        </button>
      </div>

      {/* Search */}
      <div className="glass-card p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
          <input
            type="text"
            placeholder="Search people by name or alias..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input-field pl-10"
          />
        </div>
      </div>

      {/* People Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredPeople.map((person) => (
          <div 
            key={person.id} 
            className="glass-card p-6 card-hover cursor-pointer"
            onClick={() => setSelectedPerson(person)}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-vault-500/20 flex items-center justify-center">
                  <UserCircle className="w-7 h-7 text-vault-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-100">{person.name}</h3>
                  <p className="text-sm text-slate-500">{(person.totalTransactions || 0)} transactions</p>
                </div>
              </div>
              <div className="flex gap-1">
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingPerson(person);
                  }}
                  className="p-2 rounded-lg hover:bg-dark-700 transition-colors"
                >
                  <Edit2 className="w-4 h-4 text-slate-400" />
                </button>
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeletePerson(person.id);
                  }}
                  className="p-2 rounded-lg hover:bg-red-500/20 transition-colors"
                >
                  <Trash2 className="w-4 h-4 text-red-400" />
                </button>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <p className="text-xs text-slate-500 mb-2 flex items-center gap-1">
                  <Tag className="w-3 h-3" /> Aliases
                </p>
                <div className="flex flex-wrap gap-2">
                  {person.aliases.map((alias, idx) => (
                    <span key={idx} className="px-2 py-1 text-xs bg-dark-700 text-slate-300 rounded-md">
                      {alias}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-dark-700">
                <div className="flex items-center gap-2">
                  <Wallet className="w-4 h-4 text-slate-500" />
                  <span className="text-sm text-slate-400">Monthly Fee:</span>
                  <span className="text-sm font-medium text-slate-200">
                    ETB {(person.monthlyFee || 0).toFixed(2)}
                  </span>
                </div>
                <div className="text-right">
                  <p className="text-xs text-slate-500">Total Volume</p>
                  <p className="text-sm font-semibold text-vault-400">
                    ETB {(person.totalAmount || 0).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Add Person Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="glass-card w-full max-w-md m-4">
            <div className="p-6 border-b border-dark-700">
              <h3 className="text-xl font-bold text-slate-100">Add Person</h3>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  className="input-field"
                  placeholder="Full name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">
                  Aliases (comma-separated)
                </label>
                <input
                  type="text"
                  value={formData.aliases}
                  onChange={(e) => setFormData({...formData, aliases: e.target.value})}
                  className="input-field"
                  placeholder="e.g., John, JD, Johnny"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Monthly Fee (ETB)</label>
                <input
                  type="number"
                  value={formData.monthlyFee}
                  onChange={(e) => setFormData({...formData, monthlyFee: e.target.value})}
                  className="input-field"
                  placeholder="0.00"
                />
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
                onClick={handleAddPerson}
                className="btn-primary"
              >
                Add Person
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Person Modal */}
      {editingPerson && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="glass-card w-full max-w-md m-4">
            <div className="p-6 border-b border-dark-700">
              <h3 className="text-xl font-bold text-slate-100">Edit Person</h3>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Name</label>
                <input
                  type="text"
                  value={editingPerson.name}
                  onChange={(e) => setEditingPerson({...editingPerson, name: e.target.value})}
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">
                  Aliases (comma-separated)
                </label>
                <input
                  type="text"
                  value={editingPerson.aliases.join(', ')}
                  onChange={(e) => setEditingPerson({...editingPerson, aliases: e.target.value.split(',').map(a => a.trim()).filter(a => a)})}
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Monthly Fee (ETB)</label>
                <input
                  type="number"
                  value={editingPerson.monthlyFee}
                  onChange={(e) => setEditingPerson({...editingPerson, monthlyFee: parseFloat(e.target.value) || 0})}
                  className="input-field"
                />
              </div>
            </div>
            <div className="p-6 border-t border-dark-700 flex justify-end gap-3">
              <button 
                onClick={() => setEditingPerson(null)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button 
                onClick={handleUpdatePerson}
                className="btn-primary"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Person Detail Modal */}
      {selectedPerson && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="glass-card w-full max-w-lg m-4">
            <div className="p-6 border-b border-dark-700 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-14 h-14 rounded-full bg-vault-500/20 flex items-center justify-center">
                  <UserCircle className="w-8 h-8 text-vault-400" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-slate-100">{selectedPerson.name}</h3>
                  <p className="text-sm text-slate-500">{(selectedPerson.totalTransactions || 0)} transactions</p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedPerson(null)}
                className="p-2 rounded-lg hover:bg-dark-700 transition-colors"
              >
                <span className="text-2xl text-slate-400">&times;</span>
              </button>
            </div>
            <div className="p-6 space-y-6">
              <div>
                <p className="text-sm text-slate-500 mb-3">Aliases</p>
                <div className="flex flex-wrap gap-2">
                  {selectedPerson.aliases.map((alias, idx) => (
                    <span key={idx} className="px-3 py-1.5 text-sm bg-dark-700 text-slate-300 rounded-lg">
                      {alias}
                    </span>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 bg-dark-800/50 rounded-xl text-center">
                  <p className="text-2xl font-bold text-vault-400">
                    ETB {selectedPerson.totalAmount.toLocaleString()}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Total Volume</p>
                </div>
                <div className="p-4 bg-dark-800/50 rounded-xl text-center">
                  <p className="text-2xl font-bold text-emerald-400">
                    {selectedPerson.totalTransactions}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Transactions</p>
                </div>
                <div className="p-4 bg-dark-800/50 rounded-xl text-center">
                  <p className="text-2xl font-bold text-slate-200">
                    ETB {selectedPerson.monthlyFee.toFixed(0)}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Monthly Fee</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default People;
