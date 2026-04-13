// import { useState, useCallback, useMemo } from 'react'

// const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// export default function InventoryList({ inventory, onFeedback, onSuccess }) {
//   const [searchTerm, setSearchTerm] = useState('')
//   const [removingItem, setRemovingItem] = useState(null)
//   const [loading, setLoading] = useState(false)
//   const [optimisticUpdate, setOptimisticUpdate] = useState(null)

//   const filteredInventory = useMemo(() => {
//     if (!searchTerm.trim()) return inventory
//     return inventory.filter(item => item.name.toLowerCase().includes(searchTerm.toLowerCase()))
//   }, [inventory, searchTerm])

//   const totalValue = useMemo(() => {
//     return inventory.reduce((sum, item) => sum + (item.total_value || 0), 0)
//   }, [inventory])

//   // Optimistic remove - updates UI instantly
//   const handleRemove = useCallback(async (itemName, currentQuantity) => {
//     const qty = prompt(`Remove quantity from ${itemName}\nAvailable: ${currentQuantity}`, "1")
//     if (!qty) return
    
//     const quantity = parseInt(qty)
//     if (isNaN(quantity) || quantity <= 0 || quantity > currentQuantity) {
//       onFeedback('❌ Invalid quantity')
//       return
//     }
    
//     const newQuantity = currentQuantity - quantity
//     setOptimisticUpdate({ name: itemName, newQuantity, action: 'remove', amount: quantity })
//     onFeedback(`⏳ Removing ${quantity} ${itemName}...`)
    
//     try {
//       const response = await fetch(`${API_BASE}/api/inventory/remove`, {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ name: itemName.toLowerCase(), quantity })
//       })
      
//       if (!response.ok) throw new Error('Failed')
      
//       onFeedback(`✅ Removed ${quantity} × ${itemName}`)
//       onSuccess()
//     } catch (error) {
//       onFeedback('❌ Failed to remove - reverting...')
//       onSuccess()
//     } finally {
//       setOptimisticUpdate(null)
//     }
//   }, [onFeedback, onSuccess])

//   // Optimistic add - updates UI instantly
//   const handleQuickAdd = useCallback(async (itemName) => {
//     const qty = prompt(`How many ${itemName} to add?`, "1")
//     if (!qty) return
    
//     const quantity = parseInt(qty)
//     if (isNaN(quantity) || quantity <= 0) {
//       onFeedback('❌ Invalid quantity')
//       return
//     }
    
//     const currentItem = inventory.find(i => i.name === itemName)
//     const newQuantity = (currentItem?.quantity || 0) + quantity
//     setOptimisticUpdate({ name: itemName, newQuantity, action: 'add', amount: quantity })
//     onFeedback(`⏳ Adding ${quantity} ${itemName}...`)
    
//     try {
//       const response = await fetch(`${API_BASE}/api/inventory/add`, {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ name: itemName.toLowerCase(), quantity })
//       })
      
//       if (!response.ok) throw new Error('Failed')
      
//       onFeedback(`✅ Added ${quantity} × ${itemName}`)
//       onSuccess()
//     } catch (error) {
//       onFeedback('❌ Failed to add - reverting...')
//       onSuccess()
//     } finally {
//       setOptimisticUpdate(null)
//     }
//   }, [inventory, onFeedback, onSuccess])

//   const handleDeleteAll = useCallback(async (itemName, currentQuantity) => {
//     if (!confirm(`Delete all ${currentQuantity} ${itemName}?`)) return
    
//     setOptimisticUpdate({ name: itemName, newQuantity: 0, action: 'delete', amount: currentQuantity })
//     onFeedback(`⏳ Deleting all ${itemName}...`)
    
//     try {
//       const response = await fetch(`${API_BASE}/api/inventory/remove`, {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ name: itemName.toLowerCase(), quantity: currentQuantity })
//       })
      
//       if (!response.ok) throw new Error('Failed')
      
//       onFeedback(`🗑️ Deleted all ${itemName}`)
//       onSuccess()
//     } catch (error) {
//       onFeedback('❌ Failed to delete - reverting...')
//       onSuccess()
//     } finally {
//       setOptimisticUpdate(null)
//     }
//   }, [onFeedback, onSuccess])

//   const clearSearch = () => {
//     setSearchTerm('')
//     onFeedback('🔍 Search cleared')
//   }

//   const getDisplayQuantity = (item) => {
//     if (optimisticUpdate?.name === item.name) {
//       return optimisticUpdate.newQuantity
//     }
//     return item.quantity
//   }

//   const getDisplayValue = (item) => {
//     const qty = getDisplayQuantity(item)
//     return qty * (item.price || 0)
//   }

//   // Get color class based on item name (dynamic color coding)
//   const getItemColorClass = (itemName) => {
//     const colors = ['item-purple', 'item-blue', 'item-green', 'item-orange', 'item-pink', 'item-teal']
//     const index = itemName.length % colors.length
//     return colors[index]
//   }

//   if (!inventory || inventory.length === 0 && !optimisticUpdate) {
//     return (
//       <div className="empty-inventory">
//         <div className="empty-icon">📦</div>
//         <p>No items in inventory</p>
//         <span>Add items using Voice, Text, or Camera</span>
//         <style>{`
//           .empty-inventory {
//             text-align: center;
//             padding: 40px 20px;
//             background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
//             border-radius: 24px;
//             margin-top: 16px;
//             border: 1px solid rgba(102, 126, 234, 0.2);
//             backdrop-filter: blur(10px);
//           }
//           .empty-icon { font-size: 48px; margin-bottom: 12px; opacity: 0.6; }
//           .empty-inventory p { font-size: 15px; color: #667eea; margin-bottom: 4px; font-weight: 500; }
//           .empty-inventory span { font-size: 12px; color: #8a8a8e; }
//         `}</style>
//       </div>
//     )
//   }

//   return (
//     <div className="inventory-list">
//       <div className="inventory-header">
//         <h3>📦 Inventory</h3>
//         <div className="inventory-stats">
//           <span className="stat-badge">{inventory.length} items</span>
//           <span className="stat-badge value">💰 ₹{totalValue.toFixed(2)}</span>
//         </div>
//       </div>
      
//       <div className="search-bar">
//         <input
//           type="text"
//           placeholder="🔍 Search items..."
//           value={searchTerm}
//           onChange={(e) => setSearchTerm(e.target.value)}
//         />
//         {searchTerm && (
//           <button onClick={clearSearch}>✕</button>
//         )}
//       </div>
      
//       <div className="items-list">
//         {filteredInventory.map((item) => {
//           const displayQty = getDisplayQuantity(item)
//           const displayValue = getDisplayValue(item)
//           const isUpdating = optimisticUpdate?.name === item.name
//           const colorClass = getItemColorClass(item.name)
          
//           return (
//             <div key={item.id} className={`inventory-item ${colorClass} ${isUpdating ? 'updating' : ''}`}>
//               <div className="item-info">
//                 <span className="item-name">{item.name}</span>
//                 {item.quantity <= 5 && <span className="low-stock-badge">⚠️ Low Stock</span>}
//                 <span className="item-price">₹{item.price?.toFixed(2)}/unit</span>
//               </div>
//               <div className="item-details">
//                 <span className={`item-quantity ${isUpdating ? 'pulse-animation' : ''}`}>
//                   {displayQty} {item.unit || 'units'}
//                 </span>
//                 <span className="item-value">₹{displayValue.toFixed(2)}</span>
//                 <div className="item-actions">
//                   <button 
//                     onClick={() => handleQuickAdd(item.name)}
//                     disabled={loading}
//                     className="quick-add-btn"
//                     title="Quick add"
//                   >
//                     +
//                   </button>
//                   <button 
//                     onClick={() => handleRemove(item.name, displayQty)}
//                     disabled={loading}
//                     className="remove-btn"
//                     title="Remove"
//                   >
//                     -
//                   </button>
//                   <button 
//                     onClick={() => handleDeleteAll(item.name, displayQty)}
//                     disabled={loading}
//                     className="delete-btn"
//                     title="Delete all"
//                   >
//                     🗑
//                   </button>
//                 </div>
//               </div>
//             </div>
//           )
//         })}
//       </div>

//       <style>{`
//         .inventory-list {
//           margin-top: 16px;
//           background: rgba(255, 255, 255, 0.95);
//           backdrop-filter: blur(10px);
//           border-radius: 28px;
//           padding: 24px;
//           margin-bottom: 20px;
//           box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
//           border: 1px solid rgba(102, 126, 234, 0.15);
//         }
        
//         .inventory-header {
//           display: flex;
//           justify-content: space-between;
//           align-items: center;
//           margin-bottom: 20px;
//           flex-wrap: wrap;
//           gap: 12px;
//         }
        
//         .inventory-header h3 { 
//           font-size: 1.2rem; 
//           font-weight: 600; 
//           background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
//           -webkit-background-clip: text;
//           -webkit-text-fill-color: transparent;
//           margin: 0;
//         }
        
//         .inventory-stats { 
//           display: flex; 
//           gap: 12px; 
//         }
        
//         .stat-badge {
//           padding: 6px 14px;
//           background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
//           border-radius: 30px;
//           font-size: 12px;
//           font-weight: 500;
//           color: #667eea;
//           border: 1px solid rgba(102, 126, 234, 0.2);
//         }
        
//         .stat-badge.value {
//           background: linear-gradient(135deg, #4CAF5015 0%, #2E7D3215 100%);
//           color: #2E7D32;
//           border-color: rgba(76, 175, 80, 0.2);
//         }
        
//         .search-bar {
//           display: flex;
//           gap: 10px;
//           margin-bottom: 20px;
//         }
        
//         .search-bar input {
//           flex: 1;
//           padding: 12px 18px;
//           border: 1px solid rgba(102, 126, 234, 0.2);
//           border-radius: 50px;
//           font-size: 14px;
//           background: #f8f9fa;
//           transition: all 0.3s ease;
//         }
        
//         .search-bar input:focus {
//           border-color: #667eea;
//           box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
//           outline: none;
//           background: white;
//         }
        
//         .search-bar button {
//           width: 44px;
//           background: #f0f0f5;
//           border: none;
//           border-radius: 50px;
//           cursor: pointer;
//           transition: all 0.3s ease;
//           font-size: 16px;
//         }
        
//         .search-bar button:hover { 
//           background: #e0e0e8; 
//           transform: scale(0.95);
//         }
        
//         .items-list {
//           display: flex;
//           flex-direction: column;
//           gap: 12px;
//           max-height: 500px;
//           overflow-y: auto;
//           padding-right: 4px;
//         }
        
//         /* Custom scrollbar */
//         .items-list::-webkit-scrollbar {
//           width: 6px;
//         }
        
//         .items-list::-webkit-scrollbar-track {
//           background: rgba(0, 0, 0, 0.05);
//           border-radius: 10px;
//         }
        
//         .items-list::-webkit-scrollbar-thumb {
//           background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
//           border-radius: 10px;
//         }
        
//         /* Dynamic Colorful Item Cards */
//         .inventory-item {
//           display: flex;
//           justify-content: space-between;
//           align-items: center;
//           padding: 16px 20px;
//           border-radius: 20px;
//           transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
//           cursor: pointer;
//           border: 1px solid rgba(255, 255, 255, 0.3);
//         }
        
//         .inventory-item:hover {
//           transform: translateX(6px);
//           box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
//         }
        
//         /* Purple themed items */
//         .item-purple {
//           background: linear-gradient(135deg, #f5f0ff 0%, #e8e0ff 100%);
//           border-left: 4px solid #667eea;
//         }
//         .item-purple:hover { background: linear-gradient(135deg, #ede5ff 0%, #ddd0ff 100%); }
        
//         /* Blue themed items */
//         .item-blue {
//           background: linear-gradient(135deg, #e8f4f8 0%, #d0e8f5 100%);
//           border-left: 4px solid #2196F3;
//         }
//         .item-blue:hover { background: linear-gradient(135deg, #d8ecf5 0%, #c0e0f0 100%); }
        
//         /* Green themed items */
//         .item-green {
//           background: linear-gradient(135deg, #e8f5e9 0%, #d0e8d0 100%);
//           border-left: 4px solid #4CAF50;
//         }
//         .item-green:hover { background: linear-gradient(135deg, #d8f0d9 0%, #c0e0c0 100%); }
        
//         /* Orange themed items */
//         .item-orange {
//           background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
//           border-left: 4px solid #FF9800;
//         }
//         .item-orange:hover { background: linear-gradient(135deg, #ffebd0 0%, #ffd8a0 100%); }
        
//         /* Pink themed items */
//         .item-pink {
//           background: linear-gradient(135deg, #fce4ec 0%, #f8bbd0 100%);
//           border-left: 4px solid #E91E63;
//         }
//         .item-pink:hover { background: linear-gradient(135deg, #f8d4e0 0%, #f0a8c0 100%); }
        
//         /* Teal themed items */
//         .item-teal {
//           background: linear-gradient(135deg, #e0f2f1 0%, #b2dfdb 100%);
//           border-left: 4px solid #009688;
//         }
//         .item-teal:hover { background: linear-gradient(135deg, #d0e8e5 0%, #a0d0cc 100%); }
        
//         .inventory-item.updating {
//           transform: scale(1.01);
//           filter: brightness(0.98);
//         }
        
//         .item-info { 
//           display: flex; 
//           flex-direction: column; 
//           gap: 6px; 
//         }
        
//         .item-name { 
//           font-weight: 700; 
//           text-transform: capitalize; 
//           font-size: 1rem; 
//           color: #1a1a2e;
//         }
        
//         .item-price { 
//           font-size: 11px; 
//           font-weight: 600;
//           color: #4CAF50; 
//           background: rgba(76, 175, 80, 0.15);
//           padding: 2px 8px;
//           border-radius: 20px;
//           display: inline-block;
//           width: fit-content;
//         }
        
//         .low-stock-badge { 
//           font-size: 10px; 
//           background: #f44336; 
//           color: white; 
//           padding: 2px 10px; 
//           border-radius: 20px; 
//           width: fit-content;
//           font-weight: 500;
//         }
        
//         .item-details {
//           display: flex;
//           align-items: center;
//           gap: 20px;
//           flex-wrap: wrap;
//         }
        
//         .item-quantity { 
//           font-size: 15px; 
//           font-weight: 700; 
//           color: #667eea;
//           background: rgba(102, 126, 234, 0.15);
//           padding: 4px 12px;
//           border-radius: 30px;
//         }
        
//         .item-value { 
//           font-size: 14px; 
//           font-weight: 700; 
//           color: #2e7d32;
//           background: rgba(46, 125, 50, 0.1);
//           padding: 4px 12px;
//           border-radius: 30px;
//           min-width: 80px;
//           text-align: center;
//         }
        
//         .pulse-animation {
//           animation: quantityPulse 0.3s ease;
//         }
        
//         @keyframes quantityPulse {
//           0% { transform: scale(1); background: rgba(102, 126, 234, 0.15); }
//           50% { transform: scale(1.1); background: rgba(76, 175, 80, 0.3); color: #2e7d32; }
//           100% { transform: scale(1); background: rgba(102, 126, 234, 0.15); }
//         }
        
//         .item-actions {
//           display: flex;
//           gap: 10px;
//         }
        
//         .quick-add-btn, .remove-btn, .delete-btn {
//           width: 38px;
//           height: 38px;
//           border-radius: 14px;
//           border: none;
//           cursor: pointer;
//           font-size: 18px;
//           font-weight: bold;
//           transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
//           display: flex;
//           align-items: center;
//           justify-content: center;
//         }
        
//         .quick-add-btn { 
//           background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%); 
//           color: white; 
//           box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
//         }
//         .remove-btn { 
//           background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%); 
//           color: white;
//           box-shadow: 0 2px 8px rgba(255, 152, 0, 0.3);
//         }
//         .delete-btn { 
//           background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%); 
//           color: white;
//           box-shadow: 0 2px 8px rgba(244, 67, 54, 0.3);
//         }
        
//         .quick-add-btn:hover, .remove-btn:hover, .delete-btn:hover {
//           transform: translateY(-2px) scale(1.05);
//           filter: brightness(1.05);
//         }
        
//         .quick-add-btn:active, .remove-btn:active, .delete-btn:active {
//           transform: translateY(1px) scale(0.95);
//         }
        
//         @media (max-width: 640px) {
//           .inventory-list { padding: 16px; }
//           .inventory-item { 
//             flex-direction: column; 
//             align-items: stretch; 
//             gap: 12px; 
//             padding: 14px;
//           }
//           .item-details { 
//             justify-content: space-between; 
//           }
//           .item-actions {
//             justify-content: flex-end;
//           }
//         }
//       `}</style>
//     </div>
//   )
// }
import { useState, useCallback, useMemo } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function InventoryList({ inventory, onFeedback, onSuccess }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [removingItem, setRemovingItem] = useState(null)
  const [loading, setLoading] = useState(false)
  const [optimisticUpdate, setOptimisticUpdate] = useState(null)

  const filteredInventory = useMemo(() => {
    if (!searchTerm.trim()) return inventory
    return inventory.filter(item => item.name.toLowerCase().includes(searchTerm.toLowerCase()))
  }, [inventory, searchTerm])

  const totalValue = useMemo(() => {
    return inventory.reduce((sum, item) => sum + (item.total_value || 0), 0)
  }, [inventory])

  // Optimistic remove - updates UI instantly
  const handleRemove = useCallback(async (itemName, currentQuantity) => {
    const qty = prompt(`Remove quantity from ${itemName}\nAvailable: ${currentQuantity}`, "1")
    if (!qty) return
    
    const quantity = parseInt(qty)
    if (isNaN(quantity) || quantity <= 0 || quantity > currentQuantity) {
      onFeedback('❌ Invalid quantity')
      return
    }
    
    const newQuantity = currentQuantity - quantity
    setOptimisticUpdate({ name: itemName, newQuantity, action: 'remove', amount: quantity })
    onFeedback(`⏳ Removing ${quantity} ${itemName}...`)
    
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
      onFeedback('❌ Failed to remove - reverting...')
      onSuccess()
    } finally {
      setOptimisticUpdate(null)
    }
  }, [onFeedback, onSuccess])

  // Optimistic add - updates UI instantly
  const handleQuickAdd = useCallback(async (itemName) => {
    const qty = prompt(`How many ${itemName} to add?`, "1")
    if (!qty) return
    
    const quantity = parseInt(qty)
    if (isNaN(quantity) || quantity <= 0) {
      onFeedback('❌ Invalid quantity')
      return
    }
    
    const currentItem = inventory.find(i => i.name === itemName)
    const newQuantity = (currentItem?.quantity || 0) + quantity
    setOptimisticUpdate({ name: itemName, newQuantity, action: 'add', amount: quantity })
    onFeedback(`⏳ Adding ${quantity} ${itemName}...`)
    
    try {
      const response = await fetch(`${API_BASE}/api/inventory/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: itemName.toLowerCase(), quantity })
      })
      
      if (!response.ok) throw new Error('Failed')
      
      onFeedback(`✅ Added ${quantity} × ${itemName}`)
      onSuccess()
    } catch (error) {
      onFeedback('❌ Failed to add - reverting...')
      onSuccess()
    } finally {
      setOptimisticUpdate(null)
    }
  }, [inventory, onFeedback, onSuccess])

  const handleDeleteAll = useCallback(async (itemName, currentQuantity) => {
    if (!confirm(`Delete all ${currentQuantity} ${itemName}?`)) return
    
    setOptimisticUpdate({ name: itemName, newQuantity: 0, action: 'delete', amount: currentQuantity })
    onFeedback(`⏳ Deleting all ${itemName}...`)
    
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
      onFeedback('❌ Failed to delete - reverting...')
      onSuccess()
    } finally {
      setOptimisticUpdate(null)
    }
  }, [onFeedback, onSuccess])

  const clearSearch = () => {
    setSearchTerm('')
    onFeedback('🔍 Search cleared')
  }

  // Get display quantity (with optimistic update)
  const getDisplayQuantity = (item) => {
    if (optimisticUpdate?.name === item.name) {
      return optimisticUpdate.newQuantity
    }
    return item.quantity
  }

  // Get display total value
  const getDisplayValue = (item) => {
    const qty = getDisplayQuantity(item)
    return qty * (item.price || 0)
  }

  // Get color class based on item name (dynamic color coding)
  const getItemColorClass = (itemName) => {
    const colors = ['item-purple', 'item-blue', 'item-green', 'item-orange', 'item-pink', 'item-teal']
    const index = itemName.length % colors.length
    return colors[index]
  }

  if (!inventory || inventory.length === 0 && !optimisticUpdate) {
    return (
      <div className="empty-inventory">
        <div className="empty-icon">📦</div>
        <p>No items in inventory</p>
        <span>Add items using Voice, Text, or Camera</span>
        <style>{`
          .empty-inventory {
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            border-radius: 24px;
            margin-top: 16px;
            border: 1px solid rgba(102, 126, 234, 0.2);
            backdrop-filter: blur(10px);
          }
          .empty-icon { font-size: 48px; margin-bottom: 12px; opacity: 0.6; }
          .empty-inventory p { font-size: 15px; color: #667eea; margin-bottom: 4px; font-weight: 500; }
          .empty-inventory span { font-size: 12px; color: #8a8a8e; }
        `}</style>
      </div>
    )
  }

  return (
    <div className="inventory-list">
      <div className="inventory-header">
        <h3>📦 Inventory</h3>
        <div className="inventory-stats">
          <span className="stat-badge">{inventory.length} items</span>
          <span className="stat-badge value">💰 ₹{totalValue.toFixed(2)}</span>
        </div>
      </div>
      
      <div className="search-bar">
        <input
          type="text"
          placeholder="🔍 Search items..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        {searchTerm && (
          <button onClick={clearSearch}>✕</button>
        )}
      </div>
      
      <div className="items-list">
        {filteredInventory.map((item) => {
          const displayQty = getDisplayQuantity(item)
          const displayValue = getDisplayValue(item)
          const isUpdating = optimisticUpdate?.name === item.name
          const colorClass = getItemColorClass(item.name)
          
          return (
            <div key={item.id} className={`inventory-item ${colorClass} ${isUpdating ? 'updating' : ''}`}>
              <div className="item-info">
                <span className="item-name">{item.name}</span>
                {item.quantity <= 5 && <span className="low-stock-badge">⚠️ Low Stock</span>}
                <div className="item-price-row">
                  <span className="item-price">₹{item.price?.toFixed(2)}/unit</span>
                  {item.price && (
                    <span className="item-unit-price">per {item.unit || 'piece'}</span>
                  )}
                </div>
              </div>
              <div className="item-details">
                <div className="quantity-section">
                  <span className={`item-quantity ${isUpdating ? 'pulse-animation' : ''}`}>
                    {displayQty} {item.unit || 'units'}
                  </span>
                  <span className="item-value">₹{displayValue.toFixed(2)}</span>
                </div>
                <div className="item-actions">
                  <button 
                    onClick={() => handleQuickAdd(item.name)}
                    disabled={loading}
                    className="quick-add-btn"
                    title="Quick add"
                  >
                    +
                  </button>
                  <button 
                    onClick={() => handleRemove(item.name, displayQty)}
                    disabled={loading}
                    className="remove-btn"
                    title="Remove"
                  >
                    -
                  </button>
                  <button 
                    onClick={() => handleDeleteAll(item.name, displayQty)}
                    disabled={loading}
                    className="delete-btn"
                    title="Delete all"
                  >
                    🗑
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <style>{`
        .inventory-list {
          margin-top: 16px;
          background: rgba(255, 255, 255, 0.95);
          backdrop-filter: blur(10px);
          border-radius: 28px;
          padding: 24px;
          margin-bottom: 20px;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
          border: 1px solid rgba(102, 126, 234, 0.15);
        }
        
        .inventory-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
          flex-wrap: wrap;
          gap: 12px;
        }
        
        .inventory-header h3 { 
          font-size: 1.2rem; 
          font-weight: 600; 
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          margin: 0;
        }
        
        .inventory-stats { 
          display: flex; 
          gap: 12px; 
        }
        
        .stat-badge {
          padding: 6px 14px;
          background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
          border-radius: 30px;
          font-size: 12px;
          font-weight: 500;
          color: #667eea;
          border: 1px solid rgba(102, 126, 234, 0.2);
        }
        
        .stat-badge.value {
          background: linear-gradient(135deg, #4CAF5015 0%, #2E7D3215 100%);
          color: #2E7D32;
          border-color: rgba(76, 175, 80, 0.2);
        }
        
        .search-bar {
          display: flex;
          gap: 10px;
          margin-bottom: 20px;
        }
        
        .search-bar input {
          flex: 1;
          padding: 12px 18px;
          border: 1px solid rgba(102, 126, 234, 0.2);
          border-radius: 50px;
          font-size: 14px;
          background: #f8f9fa;
          transition: all 0.3s ease;
        }
        
        .search-bar input:focus {
          border-color: #667eea;
          box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
          outline: none;
          background: white;
        }
        
        .search-bar button {
          width: 44px;
          background: #f0f0f5;
          border: none;
          border-radius: 50px;
          cursor: pointer;
          transition: all 0.3s ease;
          font-size: 16px;
        }
        
        .search-bar button:hover { 
          background: #e0e0e8; 
          transform: scale(0.95);
        }
        
        .items-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
          max-height: 500px;
          overflow-y: auto;
          padding-right: 4px;
        }
        
        .items-list::-webkit-scrollbar {
          width: 6px;
        }
        
        .items-list::-webkit-scrollbar-track {
          background: rgba(0, 0, 0, 0.05);
          border-radius: 10px;
        }
        
        .items-list::-webkit-scrollbar-thumb {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 10px;
        }
        
        /* Dynamic Colorful Item Cards */
        .inventory-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 20px;
          border-radius: 20px;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          cursor: pointer;
          border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        .inventory-item:hover {
          transform: translateX(6px);
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }
        
        /* Purple themed items */
        .item-purple {
          background: linear-gradient(135deg, #f5f0ff 0%, #e8e0ff 100%);
          border-left: 4px solid #667eea;
        }
        .item-purple:hover { background: linear-gradient(135deg, #ede5ff 0%, #ddd0ff 100%); }
        
        /* Blue themed items */
        .item-blue {
          background: linear-gradient(135deg, #e8f4f8 0%, #d0e8f5 100%);
          border-left: 4px solid #2196F3;
        }
        .item-blue:hover { background: linear-gradient(135deg, #d8ecf5 0%, #c0e0f0 100%); }
        
        /* Green themed items */
        .item-green {
          background: linear-gradient(135deg, #e8f5e9 0%, #d0e8d0 100%);
          border-left: 4px solid #4CAF50;
        }
        .item-green:hover { background: linear-gradient(135deg, #d8f0d9 0%, #c0e0c0 100%); }
        
        /* Orange themed items */
        .item-orange {
          background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
          border-left: 4px solid #FF9800;
        }
        .item-orange:hover { background: linear-gradient(135deg, #ffebd0 0%, #ffd8a0 100%); }
        
        /* Pink themed items */
        .item-pink {
          background: linear-gradient(135deg, #fce4ec 0%, #f8bbd0 100%);
          border-left: 4px solid #E91E63;
        }
        .item-pink:hover { background: linear-gradient(135deg, #f8d4e0 0%, #f0a8c0 100%); }
        
        /* Teal themed items */
        .item-teal {
          background: linear-gradient(135deg, #e0f2f1 0%, #b2dfdb 100%);
          border-left: 4px solid #009688;
        }
        .item-teal:hover { background: linear-gradient(135deg, #d0e8e5 0%, #a0d0cc 100%); }
        
        .inventory-item.updating {
          transform: scale(1.01);
          filter: brightness(0.98);
        }
        
        .item-info { 
          display: flex; 
          flex-direction: column; 
          gap: 6px; 
        }
        
        .item-name { 
          font-weight: 700; 
          text-transform: capitalize; 
          font-size: 1rem; 
          color: #1a1a2e;
        }
        
        .item-price-row {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        
        .item-price { 
          font-size: 12px; 
          font-weight: 600;
          color: #4CAF50; 
          background: rgba(76, 175, 80, 0.15);
          padding: 2px 10px;
          border-radius: 20px;
          display: inline-block;
        }
        
        .item-unit-price {
          font-size: 10px;
          color: #8a8a8e;
        }
        
        .low-stock-badge { 
          font-size: 10px; 
          background: #f44336; 
          color: white; 
          padding: 2px 10px; 
          border-radius: 20px; 
          width: fit-content;
          font-weight: 500;
        }
        
        .item-details {
          display: flex;
          align-items: center;
          gap: 20px;
          flex-wrap: wrap;
        }
        
        .quantity-section {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        
        .item-quantity { 
          font-size: 15px; 
          font-weight: 700; 
          color: #667eea;
          background: rgba(102, 126, 234, 0.15);
          padding: 4px 12px;
          border-radius: 30px;
        }
        
        .item-value { 
          font-size: 14px; 
          font-weight: 700; 
          color: #2e7d32;
          background: rgba(46, 125, 50, 0.1);
          padding: 4px 12px;
          border-radius: 30px;
          min-width: 80px;
          text-align: center;
        }
        
        .pulse-animation {
          animation: quantityPulse 0.3s ease;
        }
        
        @keyframes quantityPulse {
          0% { transform: scale(1); background: rgba(102, 126, 234, 0.15); }
          50% { transform: scale(1.1); background: rgba(76, 175, 80, 0.3); color: #2e7d32; }
          100% { transform: scale(1); background: rgba(102, 126, 234, 0.15); }
        }
        
        .item-actions {
          display: flex;
          gap: 10px;
        }
        
        .quick-add-btn, .remove-btn, .delete-btn {
          width: 38px;
          height: 38px;
          border-radius: 14px;
          border: none;
          cursor: pointer;
          font-size: 18px;
          font-weight: bold;
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
          display: flex;
          align-items: center;
          justify-content: center;
        }
        
        .quick-add-btn { 
          background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%); 
          color: white; 
          box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
        }
        .remove-btn { 
          background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%); 
          color: white;
          box-shadow: 0 2px 8px rgba(255, 152, 0, 0.3);
        }
        .delete-btn { 
          background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%); 
          color: white;
          box-shadow: 0 2px 8px rgba(244, 67, 54, 0.3);
        }
        
        .quick-add-btn:hover, .remove-btn:hover, .delete-btn:hover {
          transform: translateY(-2px) scale(1.05);
          filter: brightness(1.05);
        }
        
        .quick-add-btn:active, .remove-btn:active, .delete-btn:active {
          transform: translateY(1px) scale(0.95);
        }
        
        @media (max-width: 640px) {
          .inventory-list { padding: 16px; }
          .inventory-item { 
            flex-direction: column; 
            align-items: stretch; 
            gap: 12px; 
            padding: 14px;
          }
          .item-details { 
            justify-content: space-between; 
          }
          .quantity-section {
            flex: 1;
            justify-content: space-between;
          }
          .item-actions {
            justify-content: flex-end;
          }
        }
      `}</style>
    </div>
  )
}