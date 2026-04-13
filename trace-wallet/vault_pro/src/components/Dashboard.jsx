import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Wallet, 
  Users, 
  ArrowUpRight,
  ArrowDownRight,
  Activity,
  Clock
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalBalance: 0,
    monthlyIncome: 0,
    monthlyExpense: 0,
    pendingCount: 0,
    totalTransactions: 0,
    peopleCount: 0
  });

  const [recentTransactions, setRecentTransactions] = useState([]);
  const [chartData, setChartData] = useState([]);

  // Sample data for visualization
  useEffect(() => {
    setStats({
      totalBalance: 45678.90,
      monthlyIncome: 12500.00,
      monthlyExpense: 8320.50,
      pendingCount: 12,
      totalTransactions: 156,
      peopleCount: 24
    });

    setChartData([
      { name: 'Mon', income: 4000, expense: 2400 },
      { name: 'Tue', income: 3000, expense: 1398 },
      { name: 'Wed', income: 2000, expense: 9800 },
      { name: 'Thu', income: 2780, expense: 3908 },
      { name: 'Fri', income: 1890, expense: 4800 },
      { name: 'Sat', income: 2390, expense: 3800 },
      { name: 'Sun', income: 3490, expense: 4300 },
    ]);

    setRecentTransactions([
      { id: 1, type: 'income', amount: 2500, from: 'Salary', date: '2024-01-15', status: 'approved' },
      { id: 2, type: 'expense', amount: 150, from: 'Grocery Store', date: '2024-01-14', status: 'approved' },
      { id: 3, type: 'expense', amount: 85, from: 'Gas Station', date: '2024-01-14', status: 'pending' },
      { id: 4, type: 'expense', amount: 1200, from: 'Rent', date: '2024-01-13', status: 'approved' },
    ]);
  }, []);

  const pieData = [
    { name: 'CBE', value: 45, color: '#3b82f6' },
    { name: 'Telebirr', value: 35, color: '#a855f7' },
    { name: 'BOA', value: 20, color: '#f59e0b' },
  ];

  const StatCard = ({ title, value, icon: Icon, trend, trendValue, color }) => (
    <div className="glass-card p-6 card-hover">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-slate-400 text-sm font-medium">{title}</p>
          <h3 className="text-2xl font-bold text-slate-100 mt-2">
            {typeof value === 'number' && title.includes('Balance') 
              ? `ETB ${value.toLocaleString('en-US', { minimumFractionDigits: 2 })}`
              : value.toLocaleString()}
          </h3>
        </div>
        <div className={`p-3 rounded-xl ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
      {trend && (
        <div className="flex items-center gap-1 mt-4">
          {trend === 'up' ? (
            <ArrowUpRight className="w-4 h-4 text-emerald-400" />
          ) : (
            <ArrowDownRight className="w-4 h-4 text-red-400" />
          )}
          <span className={`text-sm ${trend === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
            {trendValue}
          </span>
          <span className="text-slate-500 text-sm">vs last month</span>
        </div>
      )}
    </div>
  );

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="Total Balance" 
          value={stats.totalBalance} 
          icon={Wallet}
          color="bg-blue-500/30"
          trend="up"
          trendValue="+12.5%"
        />
        <StatCard 
          title="Monthly Income" 
          value={stats.monthlyIncome} 
          icon={TrendingUp}
          color="bg-emerald-500/30"
          trend="up"
          trendValue="+8.2%"
        />
        <StatCard 
          title="Monthly Expense" 
          value={stats.monthlyExpense} 
          icon={TrendingDown}
          color="bg-red-500/30"
          trend="down"
          trendValue="-3.1%"
        />
        <StatCard 
          title="Pending Review" 
          value={stats.pendingCount} 
          icon={Activity}
          color="bg-yellow-500/30"
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chart */}
        <div className="lg:col-span-2 glass-card p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-6">Income vs Expense</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorIncome" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorExpense" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
                labelStyle={{ color: '#f8fafc' }}
              />
              <Area type="monotone" dataKey="income" stroke="#10b981" fillOpacity={1} fill="url(#colorIncome)" />
              <Area type="monotone" dataKey="expense" stroke="#ef4444" fillOpacity={1} fill="url(#colorExpense)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Bank Distribution */}
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-6">Bank Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-4 mt-4">
            {pieData.map((item) => (
              <div key={item.name} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
                <span className="text-sm text-slate-400">{item.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Transactions */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-slate-100">Recent Transactions</h3>
          <button className="text-vault-400 hover:text-vault-300 text-sm font-medium">
            View All
          </button>
        </div>
        <div className="space-y-4">
          {recentTransactions.map((tx) => (
            <div key={tx.id} className="flex items-center justify-between p-4 bg-dark-800/50 rounded-xl">
              <div className="flex items-center gap-4">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                  tx.type === 'income' ? 'bg-emerald-500/20' : 'bg-red-500/20'
                }`}>
                  {tx.type === 'income' ? (
                    <TrendingUp className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <TrendingDown className="w-5 h-5 text-red-400" />
                  )}
                </div>
                <div>
                  <p className="font-medium text-slate-200">{tx.from}</p>
                  <div className="flex items-center gap-2 text-sm text-slate-500">
                    <Clock className="w-3 h-3" />
                    {tx.date}
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className={`font-semibold ${tx.type === 'income' ? 'text-emerald-400' : 'text-red-400'}`}>
                  {tx.type === 'income' ? '+' : '-'}ETB {tx.amount.toFixed(2)}
                </p>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  tx.status === 'approved' ? 'status-approved' : 'status-pending'
                }`}>
                  {tx.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
