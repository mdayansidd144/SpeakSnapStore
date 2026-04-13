
import { useState, useEffect, useCallback, useMemo } from 'react'
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Dashboard({ stats, inventory, onRefresh, onFeedback }) {
  const [transactions, setTransactions] = useState([])
  const [categories, setCategories] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [loading, setLoading] = useState(false)
  const [restockingItem, setRestockingItem] = useState(null)
  const [lowStockItems, setLowStockItems] = useState([])

  const fetchTransactions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/inventory/transactions?limit=15`)
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
      setTransactions(Array.isArray(data) ? data : [])
    } catch (error) {
      setTransactions([])
    }
  }, [])

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/inventory/categories`)
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
      setCategories(Array.isArray(data) ? data : [])
    } catch (error) {
      setCategories([])
    }
  }, [])

  const fetchLowStock = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/inventory/low-stock`)
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
      setLowStockItems(Array.isArray(data) ? data : [])
    } catch (error) {
      setLowStockItems([])
    }
  }, [])

  useEffect(() => {
    fetchTransactions()
    fetchCategories()
    fetchLowStock()
  }, [fetchTransactions, fetchCategories, fetchLowStock])

  const handleRestock = useCallback(async (itemName) => {
    const qty = prompt(`How many ${itemName} to add?`, "10")
    if (!qty) return
    
    const quantity = parseInt(qty)
    if (isNaN(quantity) || quantity <= 0) {
      onFeedback('❌ Please enter a valid positive number')
      return
    }
    
    setRestockingItem(itemName)
    setLoading(true)
    
    try {
      const response = await fetch(`${API_BASE}/api/inventory/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: itemName, quantity: quantity })
      })
      
      if (!response.ok) throw new Error('Restock failed')
      
      onFeedback(`✅ Restocked ${quantity} ${itemName}`)
      onRefresh()
      fetchLowStock()
      fetchTransactions()
    } catch (error) {
      onFeedback(`❌ Failed to restock`)
    } finally {
      setRestockingItem(null)
      setLoading(false)
    }
  }, [onFeedback, onRefresh, fetchLowStock, fetchTransactions])

  const filteredInventory = useMemo(() => {
    if (!inventory || !Array.isArray(inventory)) return []
    return inventory.filter(item => {
      if (selectedCategory !== 'all' && item.category !== selectedCategory) return false
      if (searchTerm && !item.name.toLowerCase().includes(searchTerm.toLowerCase())) return false
      return true
    })
  }, [inventory, selectedCategory, searchTerm])

  const totalValue = useMemo(() => {
    if (!inventory || !Array.isArray(inventory)) return 0
    return inventory.reduce((sum, item) => sum + (item.total_value || item.quantity * (item.price || 0)), 0)
  }, [inventory])

  const clearFilters = () => {
    setSearchTerm('')
    setSelectedCategory('all')
    onFeedback('🔍 Filters cleared')
  }

  const formatTime = (timestamp) => {
    if (!timestamp) return ''
    try {
      const date = new Date(timestamp)
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return ''
    }
  }

  const statsData = useMemo(() => ({
    total_items: stats?.total_items || inventory?.length || 0,
    total_quantity: stats?.total_quantity || inventory?.reduce((sum, item) => sum + (item.quantity || 0), 0) || 0,
    total_value: stats?.total_value || totalValue,
    low_stock_items: stats?.low_stock_items || lowStockItems.length
  }), [stats, inventory, totalValue, lowStockItems.length])

  const needsRestock = lowStockItems.length > 0

  return (
    <div className="dashboard fade-in">
      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card stat-card-purple">
          <div className="stat-icon">📦</div>
          <div className="stat-value">{statsData.total_items}</div>
          <div className="stat-label">Total Items</div>
        </div>
        <div className="stat-card stat-card-blue">
          <div className="stat-icon">🔢</div>
          <div className="stat-value">{statsData.total_quantity}</div>
          <div className="stat-label">Total Units</div>
        </div>
        <div className="stat-card stat-card-orange">
          <div className="stat-icon">⚠️</div>
          <div className="stat-value">{statsData.low_stock_items}</div>
          <div className="stat-label">Low Stock</div>
        </div>
        <div className="stat-card stat-card-green">
          <div className="stat-icon">💰</div>
          <div className="stat-value">₹{statsData.total_value.toFixed(2)}</div>
          <div className="stat-label">Total Value</div>
        </div>
      </div>

      {/* Low Stock Restock Section */}
      {needsRestock && (
        <div className="restock-section">
          <h3>📋 Items Needing Restock</h3>
          <div className="restock-list">
            {lowStockItems.map(item => (
              <div key={item.id} className="restock-item">
                <span><strong>{item.name}</strong> - Only {item.quantity} left</span>
                <button 
                  className="restock-btn" 
                  onClick={() => handleRestock(item.name)} 
                  disabled={restockingItem === item.name || loading}
                >
                  {restockingItem === item.name ? '⏳...' : '➕ Restock Now'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <div className="filter-bar">
        <input
          type="text"
          placeholder="🔍 Search items..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
        <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)} className="category-select">
          <option value="all">All Categories ({categories.length})</option>
          {categories.map(cat => <option key={cat} value={cat}>{cat}</option>)}
        </select>
        {(searchTerm || selectedCategory !== 'all') && (
          <button onClick={clearFilters} className="clear-btn">✖ Clear</button>
        )}
      </div>

      {/* Filtered Items Preview */}
      <div className="filtered-preview">
        <h3>📊 Filtered Items {filteredInventory.length > 0 && `(${filteredInventory.length})`}</h3>
        {filteredInventory.length === 0 ? (
          <div className="no-items">No items match your filters</div>
        ) : (
          <div className="filtered-list">
            {filteredInventory.slice(0, 5).map(item => (
              <div key={item.id} className="filtered-item">
                <span>{item.name}</span>
                <span className="filtered-item-qty">{item.quantity} {item.unit || 'units'}</span>
              </div>
            ))}
            {filteredInventory.length > 5 && <div className="more-items">+{filteredInventory.length - 5} more items...</div>}
          </div>
        )}
      </div>

      {/* Enhanced Transactions with Price */}
      <div className="transactions-card">
        <h3>📜 Latest Transactions</h3>
        {transactions.length === 0 ? (
          <div className="no-transactions">No transactions yet. Add items to see history!</div>
        ) : (
          <div className="transaction-list">
            {transactions.slice(0, 10).map(txn => (
              <div key={txn.id} className={`transaction-item ${txn.action}`}>
                <span className="transaction-icon">{txn.action === 'add' ? '➕' : '➖'}</span>
                <div className="transaction-details">
                  <span className="transaction-name">{txn.item_name}</span>
                  <span className="transaction-qty">{txn.quantity} units</span>
                  {txn.price > 0 && (
                    <span className="transaction-price">@ ₹{txn.price.toFixed(2)}</span>
                  )}
                  {txn.total_value > 0 && (
                    <span className="transaction-value">₹{txn.total_value.toFixed(2)}</span>
                  )}
                </div>
                <span className="transaction-time">{formatTime(txn.timestamp)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <style>{`
        .stats-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          margin-bottom: 24px;
        }
        
        .stat-card {
          padding: 20px 16px;
          border-radius: 20px;
          text-align: center;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          color: white;
          cursor: pointer;
        }
        
        .stat-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 12px 28px rgba(0, 0, 0, 0.15);
        }
        
        .stat-card-purple { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .stat-card-blue { background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%); }
        .stat-card-orange { background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%); }
        .stat-card-green { background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%); }
        
        .stat-icon { font-size: 2rem; margin-bottom: 8px; }
        .stat-value { font-size: 1.8rem; font-weight: 700; }
        .stat-label { font-size: 0.8rem; opacity: 0.9; margin-top: 4px; }
        
        .restock-section {
          background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%);
          border-radius: 20px;
          padding: 16px;
          margin-bottom: 24px;
        }
        
        .restock-section h3 { margin: 0 0 12px 0; color: #E65100; font-size: 0.9rem; }
        .restock-list { display: flex; flex-direction: column; gap: 10px; }
        .restock-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          background: white;
          padding: 12px 16px;
          border-radius: 14px;
          flex-wrap: wrap;
          gap: 10px;
        }
        .restock-btn {
          background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);
          color: white;
          border: none;
          padding: 8px 20px;
          border-radius: 30px;
          cursor: pointer;
          transition: all 0.2s;
        }
        .restock-btn:hover { transform: scale(1.02); box-shadow: 0 2px 8px rgba(255,152,0,0.3); }
        
        .filter-bar {
          display: flex;
          gap: 10px;
          margin-bottom: 20px;
          flex-wrap: wrap;
        }
        .search-input {
          flex: 1;
          padding: 12px 16px;
          border: 1px solid #e0e0e0;
          border-radius: 40px;
          font-size: 14px;
          background: white;
          transition: all 0.2s;
        }
        .search-input:focus { border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
        .category-select {
          padding: 12px 16px;
          border: 1px solid #e0e0e0;
          border-radius: 40px;
          background: white;
          cursor: pointer;
        }
        .clear-btn {
          padding: 12px 20px;
          background: #f5f5f5;
          border: none;
          border-radius: 40px;
          cursor: pointer;
          transition: all 0.2s;
        }
        .clear-btn:hover { background: #e0e0e0; transform: scale(0.98); }
        
        .filtered-preview {
          background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
          padding: 16px;
          border-radius: 20px;
          margin-bottom: 24px;
        }
        .filtered-preview h3 { margin: 0 0 12px 0; font-size: 1rem; }
        .filtered-list { display: flex; flex-direction: column; gap: 8px; }
        .filtered-item {
          display: flex;
          justify-content: space-between;
          padding: 10px 12px;
          background: white;
          border-radius: 12px;
        }
        .filtered-item-qty {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          padding: 2px 10px;
          border-radius: 20px;
          font-size: 12px;
          color: white;
        }
        .more-items { text-align: center; color: #667eea; font-size: 12px; padding: 8px; }
        .no-items { text-align: center; color: #aaa; padding: 24px; }
        
        .transactions-card {
          background: white;
          padding: 16px;
          border-radius: 20px;
          border: 1px solid rgba(102, 126, 234, 0.1);
        }
        .transactions-card h3 { margin: 0 0 12px 0; font-size: 1rem; }
        .transaction-list { display: flex; flex-direction: column; gap: 8px; max-height: 350px; overflow-y: auto; }
        .transaction-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px;
          background: #f8f9fa;
          border-radius: 12px;
          transition: all 0.2s;
        }
        .transaction-item:hover { background: #f0f0f5; transform: translateX(4px); }
        .transaction-item.add { border-left: 3px solid #4CAF50; }
        .transaction-item.remove { border-left: 3px solid #f44336; }
        .transaction-icon { font-size: 1.1rem; min-width: 30px; }
        .transaction-details { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; flex: 1; }
        .transaction-name { font-weight: 600; text-transform: capitalize; min-width: 100px; }
        .transaction-qty { color: #666; font-size: 12px; }
        .transaction-price { font-size: 11px; color: #FF9800; background: rgba(255,152,0,0.1); padding: 2px 8px; border-radius: 12px; }
        .transaction-value { font-size: 12px; font-weight: 600; color: #4CAF50; background: rgba(76,175,80,0.1); padding: 2px 10px; border-radius: 12px; }
        .transaction-time { font-size: 11px; color: #aaa; min-width: 100px; text-align: right; }
        .no-transactions { text-align: center; color: #aaa; padding: 24px; }
        
        @media (max-width: 640px) {
          .stats-grid { gap: 12px; }
          .stat-card { padding: 14px 10px; }
          .stat-value { font-size: 1.4rem; }
          .transaction-details { flex-wrap: wrap; gap: 6px; }
          .transaction-time { min-width: auto; }
        }
      `}</style>
    </div>
  )
}