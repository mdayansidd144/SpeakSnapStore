import { useState, useCallback, useMemo } from 'react'
const API_BASE = 'https://speak-snap-backend.onrender.com'
export default function InventoryList({ inventory, onFeedback, onSuccess }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [removingItem, setRemovingItem] = useState(null)
  const [addingItem, setAddingItem] = useState(null)
  const [loading, setLoading] = useState(false)
  const filteredInventory = useMemo(() => {
    if (!searchTerm.trim()) return inventory
    return inventory.filter(item => item.name.toLowerCase().includes(searchTerm.toLowerCase()))
  }, [inventory, searchTerm])
  const totalValue = useMemo(() => {
    return inventory.reduce((sum, item) => sum + (item.total_value || 0), 0)
  }, [inventory])
  const handleRemove = useCallback(async (itemName, currentQuantity) => {
    const qty = prompt(`Remove quantity from ${itemName}\nAvailable: ${currentQuantity}`, "1")
    if (!qty) return
  
    const quantity = parseInt(qty)
    if (isNaN(quantity) || quantity <= 0 || quantity > currentQuantity) {
      onFeedback('❌ Invalid quantity')
      return
    }
    setRemovingItem(itemName)
    setLoading(true)
    
    try {
      const response = await fetch(`${API_BASE}/api/inventory/remove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: itemName.toLowerCase(), quantity })
      })
      
      if (!response.ok) throw new Error('Failed')
      
      onFeedback(`✅ Removed ${quantity} × ${itemName}`)
      onSuccess()
    } catch (error) {
      onFeedback('❌ Failed to remove')
    } finally {
      setRemovingItem(null)
      setLoading(false)
    }
  }, [onFeedback, onSuccess])

  const handleDeleteAll = useCallback(async (itemName, currentQuantity) => {
    if (!confirm(`Delete all ${currentQuantity} ${itemName}?`)) return
    
    setRemovingItem(itemName)
    setLoading(true)
    
    try {
      const response = await fetch(`${API_BASE}/api/inventory/remove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: itemName.toLowerCase(), quantity: currentQuantity })
      })
      
      if (!response.ok) throw new Error('Failed')
      
      onFeedback(`🗑️ Deleted all ${itemName}`)
      onSuccess()
    } catch (error) {
      onFeedback('❌ Failed to delete')
    } finally {
      setRemovingItem(null)
      setLoading(false)
    }
  }, [onFeedback, onSuccess])

  if (!inventory || inventory.length === 0) {
    return (
      <div className="empty-inventory">
        <div className="empty-icon">📦</div>
        <p>No items in inventory</p>
        <span>Add items using Voice or Camera</span>
        <style>{`
          .empty-inventory {
            text-align: center;
            padding: 40px 20px;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 20px;
            margin-top: 16px;
            backdrop-filter: blur(10px);
            animation: fadeIn 0.5s ease;
          }
          .empty-icon {
            font-size: 48px;
            margin-bottom: 12px;
            opacity: 0.5;
          }
          .empty-inventory p {
            font-size: 15px;
            color: #1c1c1e;
            margin-bottom: 4px;
          }
          .empty-inventory span {
            font-size: 12px;
            color: #999;
          }
          @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
          }
        `}</style>
      </div>
    )
  }

  return (
    <div className="inventory-list">
      <div className="inventory-header">
        <h3>Inventory</h3>
        <div className="inventory-stats">
          <span>{inventory.length} items</span>
          <span>₹{totalValue.toFixed(2)}</span>
        </div>
      </div>
      
      <div className="search-bar">
        <input
          type="text"
          placeholder="Search items..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        {searchTerm && (
          <button onClick={() => setSearchTerm('')}>✕</button>
        )}
      </div>
      
      <div className="items-list">
        {filteredInventory.map((item) => (
          <div 
            key={item.id} 
            className={`inventory-item ${removingItem === item.name ? 'removing' : ''} ${addingItem === item.name ? 'adding' : ''}`}
          >
            <div className="item-info">
              <span className="item-name">{item.name}</span>
              {item.quantity <= 5 && <span className="low-stock-badge">Low</span>}
            </div>
            <div className="item-details">
              <span className="item-quantity">{item.quantity} {item.unit || 'units'}</span>
              <span className="item-value">₹{(item.quantity * (item.price || 0)).toFixed(2)}</span>
              <div className="item-actions">
                <button 
                  onClick={() => handleRemove(item.name, item.quantity)}
                  disabled={removingItem === item.name || loading}
                  className="remove-btn"
                  title="Remove quantity"
                >
                  -
                </button>
                <button 
                  onClick={() => handleDeleteAll(item.name, item.quantity)}
                  disabled={removingItem === item.name || loading}
                  className="delete-btn"
                  title="Delete all"
                >
                  🗑
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <style>{`
        .inventory-list {
          margin-top: 16px;
          background: rgba(255, 255, 255, 0.9);
          backdrop-filter: blur(10px);
          border-radius: 20px;
          padding: 16px;
          margin-bottom: 20px;
          border: 1px solid rgba(0, 0, 0, 0.05);
        }
        
        .inventory-header {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          margin-bottom: 12px;
        }
        
        .inventory-header h3 {
          font-size: 16px;
          font-weight: 600;
        }
        
        .inventory-stats {
          display: flex;
          gap: 12px;
          font-size: 12px;
          color: #20B2AA;
        }
        
        .search-bar {
          display: flex;
          gap: 8px;
          margin-bottom: 16px;
        }
        
        .search-bar input {
          flex: 1;
          padding: 10px 14px;
          border: 1px solid rgba(0, 0, 0, 0.1);
          border-radius: 12px;
          font-size: 14px;
          background: white;
          transition: all 0.3s ease;
        }
        
        .search-bar input:focus {
          outline: none;
          border-color: #20B2AA;
          box-shadow: 0 0 0 2px rgba(32, 178, 170, 0.2);
        }
        
        .search-bar button {
          width: 40px;
          background: #f0f0f0;
          border: none;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        
        .search-bar button:hover {
          background: #e0e0e0;
          transform: scale(0.95);
        }
        
        .items-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
          max-height: 400px;
          overflow-y: auto;
        }
        
        /* Item Card Styles with Hover Effect */
        .inventory-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px;
          background: white;
          border-radius: 14px;
          border: 1px solid rgba(0, 0, 0, 0.05);
          transition: all 0.3s ease;
          cursor: pointer;
        }
        
        /* Hover Effect */
        .inventory-item:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          border-color: #20B2AA;
          background: linear-gradient(135deg, #ffffff 0%, #f8fffe 100%);
        }
        
        /* Click Effect */
        .inventory-item:active {
          transform: scale(0.98);
          transition: transform 0.05s ease;
        }
        
        /* Adding Animation (when item is added) */
        .inventory-item.adding {
          animation: addPulse 0.6s ease;
          background: linear-gradient(135deg, #e8f8f0 0%, #d0f0e0 100%);
          border-color: #4CAF50;
        }
        
        /* Removing Animation */
        .inventory-item.removing {
          animation: removeShake 0.4s ease;
          background: linear-gradient(135deg, #fff0f0 0%, #ffe0e0 100%);
          border-color: #f44336;
        }
        
        @keyframes addPulse {
          0% {
            transform: scale(1);
            background: white;
          }
          50% {
            transform: scale(1.02);
            background: linear-gradient(135deg, #e8f8f0 0%, #c8e8d8 100%);
            box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.3);
          }
          100% {
            transform: scale(1);
            background: white;
          }
        }
        
        @keyframes removeShake {
          0% { transform: translateX(0); }
          25% { transform: translateX(-3px); background: #ffe0e0; }
          75% { transform: translateX(3px); background: #ffe0e0; }
          100% { transform: translateX(0); background: white; }
        }
        
        .item-info {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        
        .item-name {
          font-weight: 600;
          text-transform: capitalize;
          transition: color 0.3s ease;
        }
        
        .inventory-item:hover .item-name {
          color: #20B2AA;
        }
        
        .low-stock-badge {
          font-size: 10px;
          background: #f44336;
          color: white;
          padding: 2px 8px;
          border-radius: 20px;
          width: fit-content;
          transition: all 0.3s ease;
        }
        
        .inventory-item:hover .low-stock-badge {
          transform: scale(1.05);
        }
        
        .item-details {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        
        .item-quantity {
          font-size: 14px;
          color: #1c1c1e;
          transition: all 0.3s ease;
        }
        
        .inventory-item:hover .item-quantity {
          font-weight: 600;
          color: #20B2AA;
        }
        
        .item-value {
          font-size: 13px;
          font-weight: 600;
          color: #4CAF50;
          transition: all 0.3s ease;
        }
        
        .inventory-item:hover .item-value {
          transform: scale(1.05);
          color: #2E7D32;
        }
        
        .item-actions {
          display: flex;
          gap: 6px;
        }
        
        .remove-btn, .delete-btn {
          width: 32px;
          height: 32px;
          border-radius: 10px;
          border: none;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.2s ease;
        }
        
        .remove-btn {
          background: #ff9800;
          color: white;
        }
        
        .remove-btn:hover {
          background: #f57c00;
          transform: scale(1.05);
        }
        
        .delete-btn {
          background: #f44336;
          color: white;
        }
        
        .delete-btn:hover {
          background: #d32f2f;
          transform: scale(1.05);
        }
        
        .remove-btn:active, .delete-btn:active {
          transform: scale(0.95);
        }
        
        /* Scrollbar Styling */
        .items-list::-webkit-scrollbar {
          width: 4px;
        }
        
        .items-list::-webkit-scrollbar-track {
          background: rgba(0, 0, 0, 0.05);
          border-radius: 4px;
        }
        
        .items-list::-webkit-scrollbar-thumb {
          background: #20B2AA;
          border-radius: 4px;
        }
      `}</style>
    </div>
  )
}