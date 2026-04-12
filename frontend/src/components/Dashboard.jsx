import { useState, useEffect, useCallback, useMemo } from 'react'
const API_BASE = 'http://localhost:8000'
export default function Dashboard({ stats, inventory, onRefresh, onFeedback }) {
  const [transactions, setTransactions] = useState([])
  const [categories, setCategories] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [loading, setLoading] = useState(false)
  const [restockingItem, setRestockingItem] = useState(null)
  const [exporting, setExporting] = useState(false)

  const fetchTransactions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/inventory/transactions?limit=10`)
      if (!res.ok) throw new Error('Failed to fetch')
      const data = await res.json()
      setTransactions(Array.isArray(data) ? data : [])
    } catch (error) {
      console.error('Failed to fetch transactions:', error)
      setTransactions([])
    }
  }, [])

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/inventory/categories`)
      if (!res.ok) throw new Error('Failed to fetch')
      const data = await res.json()
      setCategories(Array.isArray(data) ? data : [])
    } catch (error) {
      console.error('Failed to fetch categories:', error)
      setCategories([])
    }
  }, [])

  useEffect(() => {
    fetchTransactions()
    fetchCategories()
  }, [fetchTransactions, fetchCategories])

  const exportToJSON = async () => {
    setExporting(true)
    onFeedback('📁 Exporting to JSON...')
    try {
      const res = await fetch(`${API_BASE}/api/inventory/export/json`)
      const data = await res.json()
      if (data.success) {
        onFeedback(`✅ Exported to JSON`)
      } else {
        onFeedback('❌ JSON export failed')
      }
    } catch (error) {
      onFeedback('❌ JSON export failed')
    }
    setExporting(false)
  }

  const exportToCSV = async () => {
    setExporting(true)
    onFeedback('📊 Exporting to CSV...')
    try {
      const res = await fetch(`${API_BASE}/api/inventory/export/csv`)
      const data = await res.json()
      if (data.success) {
        onFeedback(`✅ Exported to CSV`)
      } else {
        onFeedback('❌ CSV export failed')
      }
    } catch (error) {
      onFeedback('❌ CSV export failed')
    }
    setExporting(false)
  }

  const exportToTXT = async () => {
    setExporting(true)
    onFeedback('📝 Exporting to TXT...')
    try {
      const res = await fetch(`${API_BASE}/api/inventory/export/txt`)
      const data = await res.json()
      if (data.success) {
        onFeedback(`✅ Exported to TXT`)
      } else {
        onFeedback('❌ TXT export failed')
      }
    } catch (error) {
      onFeedback('❌ TXT export failed')
    }
    setExporting(false)
  }

  const exportAllFormats = async () => {
    setExporting(true)
    onFeedback('📦 Exporting all formats...')
    try {
      const res = await fetch(`${API_BASE}/api/inventory/export/all`)
      const data = await res.json()
      if (data.success) {
        onFeedback(`✅ Exported all formats`)
      }
    } catch (error) {
      onFeedback('❌ Export failed')
    }
    setExporting(false)
  }

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
    } catch (error) {
      onFeedback(`❌ Failed to restock`)
    } finally {
      setRestockingItem(null)
      setLoading(false)
    }
  }, [onFeedback, onRefresh])

  const filteredInventory = useMemo(() => {
    if (!inventory || !Array.isArray(inventory)) return []
    return inventory.filter(item => {
      if (selectedCategory !== 'all' && item.category !== selectedCategory) return false
      if (searchTerm && !item.name.toLowerCase().includes(searchTerm.toLowerCase())) return false
      return true
    })
  }, [inventory, selectedCategory, searchTerm])

  const lowStockItems = useMemo(() => {
    if (!inventory || !Array.isArray(inventory)) return []
    return inventory.filter(item => item.quantity <= 5)
  }, [inventory])

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
      return new Date(timestamp).toLocaleTimeString()
    } catch {
      return ''
    }
  }

  const statsData = useMemo(() => ({
    total_items: stats?.total_items || inventory?.length || 0,
    total_quantity: stats?.total_quantity || inventory?.reduce((sum, item) => sum + (item.quantity || 0), 0) || 0,
    total_value: stats?.total_value || totalValue
  }), [stats, inventory, totalValue])

  return (
    <div className="dashboard">
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">📦</div>
          <div className="stat-value">{statsData.total_items}</div>
          <div className="stat-label">Total Items</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🔢</div>
          <div className="stat-value">{statsData.total_quantity}</div>
          <div className="stat-label">Total Units</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">⚠️</div>
          <div className="stat-value">{lowStockItems.length}</div>
          <div className="stat-label">Low Stock</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">💰</div>
          <div className="stat-value">₹{statsData.total_value.toFixed(2)}</div>
          <div className="stat-label">Total Value</div>
        </div>
      </div>

      {lowStockItems.length > 0 && (
        <div className="alert-card">
          <h3>⚠️ Low Stock Alert</h3>
          <div className="low-stock-list">
            {lowStockItems.map(item => (
              <div key={item.id} className="low-stock-item">
                <span><strong>{item.name}</strong></span>
                <span className="low-stock-qty">Only {item.quantity} left</span>
                <button className="restock-btn" onClick={() => handleRestock(item.name)} disabled={restockingItem === item.name || loading}>
                  {restockingItem === item.name ? '⏳...' : '➕ Restock'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="filter-bar">
        <input type="text" placeholder="🔍 Search items..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="search-input" />
        <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)} className="category-select">
          <option value="all">All Categories ({categories.length})</option>
          {categories.map(cat => <option key={cat} value={cat}>{cat}</option>)}
        </select>
        
        <div className="export-buttons">
          <button onClick={exportToJSON} className="export-json" disabled={exporting}>📄 JSON</button>
          <button onClick={exportToCSV} className="export-csv" disabled={exporting}>📊 CSV</button>
          <button onClick={exportToTXT} className="export-txt" disabled={exporting}>📝 TXT</button>
          <button onClick={exportAllFormats} className="export-all" disabled={exporting}>📦 All</button>
        </div>
        
        {(searchTerm || selectedCategory !== 'all') && (
          <button onClick={clearFilters} className="clear-btn">✖ Clear Filters</button>
        )}
      </div>

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

      <div className="transactions-card">
        <h3>📜 Recent Transactions</h3>
        {transactions.length === 0 ? (
          <div className="no-transactions">No transactions yet</div>
        ) : (
          <div className="transaction-list">
            {transactions.slice(0, 10).map(txn => (
              <div key={txn.id} className={`transaction-item ${txn.action}`}>
                <span className="transaction-action">{txn.action === 'add' ? '➕' : '➖'}</span>
                <span className="transaction-item-name">{txn.item_name}</span>
                <span className="transaction-quantity">{txn.quantity} units</span>
                <span className="transaction-time">{formatTime(txn.timestamp)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <style>{`

  .stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  backdrop-filter: blur(10px);
  padding: 16px 12px;
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(32, 178, 170, 0.2);
  transition: all 0.3s ease;
}

.stat-icon {
  font-size: 28px;
  margin-bottom: 6px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #ececec;
}

.stat-label {
  font-size: 11px;
  color: #20B2AA;
  margin-top: 4px;
  font-weight: 500;
  white-space: nowrap;
}
        .stat-icon { font-size: 2rem; margin-bottom: 10px; }
        .stat-value { font-size: 2rem; font-weight: bold; }
        .stat-label { font-size: 0.8rem; opacity: 0.9; }
        .alert-card { background: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
        .alert-card h3 { margin: 0 0 10px 0; color: #ff9800; }
        .low-stock-list { display: flex; flex-direction: column; gap: 10px; }
        .low-stock-item { display: flex; justify-content: space-between; align-items: center; padding: 10px; background: white; border-radius: 8px; flex-wrap: wrap; gap: 10px; }
        .low-stock-qty { color: #f44336; font-weight: bold; }
        .restock-btn { background: #4CAF50; color: white; border: none; padding: 6px 15px; border-radius: 5px; cursor: pointer; }
        .filter-bar { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .search-input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 8px; min-width: 150px; }
        .category-select { padding: 10px; border: 1px solid #ddd; border-radius: 8px; background: white; cursor: pointer; }
        .export-buttons { display: flex; gap: 8px; flex-wrap: wrap; }
        .export-json, .export-csv, .export-txt, .export-all, .clear-btn { padding: 10px 16px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; }
        .export-json { background: #2196F3; color: white; }
        .export-csv { background: #4CAF50; color: white; }
        .export-txt { background: #FF9800; color: white; }
        .export-all { background: #9C27B0; color: white; }
        .clear-btn { background: #f44336; color: white; }
        .filtered-preview { background: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
        .filtered-preview h3 { margin: 0 0 10px 0; }
        .filtered-list { display: flex; flex-direction: column; gap: 8px; }
        .filtered-item { display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #eee; }
        .filtered-item-qty { background: #e0e0e0; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
        .more-items { text-align: center; color: #666; font-size: 12px; padding: 8px; }
        .no-items { text-align: center; color: #999; padding: 20px; }
        .transactions-card { background: white; padding: 15px; border-radius: 10px; }
        .transactions-card h3 { margin: 0 0 10px 0; }
        .transaction-list { display: flex; flex-direction: column; gap: 8px; max-height: 300px; overflow-y: auto; }
        .transaction-item { display: flex; align-items: center; gap: 15px; padding: 10px; border-bottom: 1px solid #eee; }
        .transaction-item.add { border-left: 3px solid #4CAF50; }
        .transaction-item.remove { border-left: 3px solid #f44336; }
        .transaction-action { font-size: 1.2rem; }
        .transaction-item-name { flex: 1; font-weight: 500; }
        .transaction-quantity { color: #666; }
        .transaction-time { font-size: 0.7rem; color: #999; }
        .no-transactions { text-align: center; color: #999; padding: 30px; }
      `}</style>
    </div>
  )
}
