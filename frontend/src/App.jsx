// import { useState, useEffect, useCallback } from 'react'
// import VoiceAssistant from './components/VoiceAssistant'
// import CameraDetector from './components/CameraDetector'
// import InventoryList from './components/InventoryList'
// import FeedbackMessage from './components/FeedbackMessage'
// import Dashboard from './components/Dashboard'
// import './App.css'

// const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// function App() {
//   const [activeTab, setActiveTab] = useState('dashboard')
//   const [inventory, setInventory] = useState([])
//   const [feedback, setFeedback] = useState('')
//   const [stats, setStats] = useState(null)
//   const [loading, setLoading] = useState(false)
//   const [error, setError] = useState(null)

//   const refreshInventory = useCallback(async () => {
//     try {
//       setLoading(true)
//       const res = await fetch(`${API_BASE}/api/inventory/`)
      
//       if (!res.ok) {
//         throw new Error(`HTTP ${res.status}: ${res.statusText}`)
//       }
      
//       const data = await res.json()
//       setInventory(Array.isArray(data) ? data : [])
//       setError(null)
//     } catch (error) {
//       console.error('Failed to fetch inventory:', error)
//       setError(error.message)
//       setInventory([])
//     } finally {
//       setLoading(false)
//     }
//   }, [])

//   const refreshStats = useCallback(async () => {
//     try {
//       const res = await fetch(`${API_BASE}/api/inventory/stats`)
      
//       if (!res.ok) {
//         throw new Error(`HTTP ${res.status}: ${res.statusText}`)
//       }
      
//       const data = await res.json()
//       setStats(data)
//     } catch (error) {
//       console.error('Failed to fetch stats:', error)
//       setStats({ 
//         total_items: 0, 
//         total_quantity: 0, 
//         total_value: 0, 
//         low_stock_items: 0 
//       })
//     }
//   }, [])

//   useEffect(() => {
//     refreshInventory()
//     refreshStats()
//   }, [refreshInventory, refreshStats])

//   const handleTabChange = (tab) => {
//     setActiveTab(tab)
//     setFeedback(`Switched to ${tab} mode`)
//   }

//   // Dynamic background based on active tab
//   const getAppClass = () => {
//     switch(activeTab) {
//       case 'dashboard': return 'app dashboard'
//       case 'voice': return 'app voice'
//       case 'camera': return 'app camera'
//       default: return 'app'
//     }
//   }

//   return (
//     <div className={getAppClass()}>
//       <header>
//         <div className="logo-section">
//           <h1>🎙️ Speak Snap Store</h1>
//           <p>Voice • Vision • Intelligence • Real-time Inventory</p>
//         </div>
//         {loading && (
//           <div className="loading-indicator">
//             <span className="spinner"></span>
//             <span>Syncing...</span>
//           </div>
//         )}
//       </header>

//       <div className="tabs">
//         <button 
//           className={activeTab === 'dashboard' ? 'active' : ''} 
//           onClick={() => handleTabChange('dashboard')}
//         >
//           <span className="tab-icon">📊</span>
//           <span className="tab-label">Dashboard</span>
//         </button>
//         <button 
//           className={activeTab === 'voice' ? 'active' : ''} 
//           onClick={() => handleTabChange('voice')}
//         >
//           <span className="tab-icon">🎤</span>
//           <span className="tab-label">Voice</span>
//         </button>
//         <button 
//           className={activeTab === 'camera' ? 'active' : ''} 
//           onClick={() => handleTabChange('camera')}
//         >
//           <span className="tab-icon">📸</span>
//           <span className="tab-label">Camera</span>
//         </button>
//       </div>

//       <div className="main-content">
//         {error && (
//           <div className="error-banner">
//             <span>⚠️</span>
//             <span>Connection error: {error}</span>
//             <button onClick={() => { refreshInventory(); refreshStats(); }}>Retry</button>
//           </div>
//         )}
        
//         {activeTab === 'dashboard' && (
//           <Dashboard 
//             stats={stats} 
//             inventory={inventory} 
//             onRefresh={refreshInventory} 
//             onFeedback={setFeedback} 
//           />
//         )}
//         {activeTab === 'voice' && (
//           <VoiceAssistant 
//             onFeedback={setFeedback} 
//             onSuccess={() => { 
//               refreshInventory(); 
//               refreshStats(); 
//             }} 
//           />
//         )}
//         {activeTab === 'camera' && (
//           <CameraDetector 
//             onFeedback={setFeedback} 
//             onSuccess={() => { 
//               refreshInventory(); 
//               refreshStats(); 
//             }} 
//           />
//         )}
//       </div>

//       <InventoryList 
//         inventory={inventory} 
//         onFeedback={setFeedback}
//         onSuccess={() => { 
//           refreshInventory(); 
//           refreshStats(); 
//         }}
//       />
//       <FeedbackMessage message={feedback} />
      
//       <style>{`
//         .logo-section {
//           text-align: center;
//         }
        
//         .loading-indicator {
//           position: absolute;
//           top: 20px;
//           right: 20px;
//           display: flex;
//           align-items: center;
//           gap: 8px;
//           background: rgba(255, 255, 255, 0.9);
//           padding: 6px 12px;
//           border-radius: 30px;
//           font-size: 12px;
//           color: #667eea;
//         }
        
//         .spinner {
//           width: 16px;
//           height: 16px;
//           border: 2px solid #e0e0e0;
//           border-top-color: #667eea;
//           border-radius: 50%;
//           animation: spin 0.8s linear infinite;
//         }
        
//         @keyframes spin {
//           to { transform: rotate(360deg); }
//         }
        
//         .error-banner {
//           background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
//           border-left: 4px solid #f44336;
//           padding: 12px 16px;
//           border-radius: 12px;
//           margin-bottom: 20px;
//           display: flex;
//           align-items: center;
//           gap: 12px;
//           font-size: 13px;
//           color: #c62828;
//         }
        
//         .error-banner button {
//           margin-left: auto;
//           background: #f44336;
//           color: white;
//           border: none;
//           padding: 4px 12px;
//           border-radius: 20px;
//           cursor: pointer;
//           font-size: 12px;
//           transition: all 0.2s;
//         }
        
//         .error-banner button:hover {
//           background: #d32f2f;
//           transform: scale(1.02);
//         }
        
//         .tab-icon {
//           font-size: 1.1rem;
//         }
        
//         .tab-label {
//           margin-left: 6px;
//         }
        
//         @media (max-width: 640px) {
//           .tab-label {
//             display: none;
//           }
//           .tab-icon {
//             font-size: 1.3rem;
//           }
//           .loading-indicator {
//             top: 10px;
//             right: 10px;
//             padding: 4px 8px;
//             font-size: 10px;
//           }
//         }
//       `}</style>
//     </div>
//   )
// }

// export default App
import { useState, useEffect, useCallback } from 'react'
import VoiceAssistant from './components/VoiceAssistant'
import CameraDetector from './components/CameraDetector'
import InventoryList from './components/InventoryList'
import FeedbackMessage from './components/FeedbackMessage'
import Dashboard from './components/Dashboard'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [inventory, setInventory] = useState([])
  const [feedback, setFeedback] = useState('')
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const refreshInventory = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/api/inventory/`)
      
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      }
      
      const data = await res.json()
      setInventory(Array.isArray(data) ? data : [])
      setError(null)
    } catch (error) {
      console.error('Failed to fetch inventory:', error)
      setError(error.message)
      setInventory([])
    } finally {
      setLoading(false)
    }
  }, [])

  const refreshStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/inventory/stats`)
      
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      }
      
      const data = await res.json()
      setStats(data)
    } catch (error) {
      console.error('Failed to fetch stats:', error)
      setStats({ 
        total_items: 0, 
        total_quantity: 0, 
        total_value: 0, 
        low_stock_items: 0 
      })
    }
  }, [])

  useEffect(() => {
    refreshInventory()
    refreshStats()
  }, [refreshInventory, refreshStats])

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    setFeedback(`Switched to ${tab} mode`)
  }

  const getAppClass = () => {
    switch(activeTab) {
      case 'dashboard': return 'app dashboard'
      case 'voice': return 'app voice'
      case 'camera': return 'app camera'
      default: return 'app'
    }
  }

  return (
    <div className={getAppClass()}>
      <header>
  <div className="logo-section">
    <h1 className="ocean-flashcard-title">
      <span className="ocean-word">🎙️ Speak</span>
      <span className="ocean-word">Snap</span>
      <span className="ocean-word">Stock</span>
    </h1>
    <div className="tagline-flashcard">
      <span className="tagline-word">Voice</span>
      <span className="tagline-word">Vision</span>
      <span className="tagline-word">Intelligence</span>
      <span className="tagline-word ocean-highlight">Real-time Inventory</span>
    </div>
  </div>
  {loading && (
    <div className="loading-indicator">
      <span className="spinner"></span>
      <span>Syncing...</span>
    </div>
  )}
</header>

      <div className="tabs">
        <button 
          className={activeTab === 'dashboard' ? 'active' : ''} 
          onClick={() => handleTabChange('dashboard')}
        >
          <span className="tab-icon">📊</span>
          <span className="tab-label">Dashboard</span>
        </button>
        <button 
          className={activeTab === 'voice' ? 'active' : ''} 
          onClick={() => handleTabChange('voice')}
        >
          <span className="tab-icon">🎤</span>
          <span className="tab-label">Voice</span>
        </button>
        <button 
          className={activeTab === 'camera' ? 'active' : ''} 
          onClick={() => handleTabChange('camera')}
        >
          <span className="tab-icon">📸</span>
          <span className="tab-label">Camera</span>
        </button>
      </div>

      <div className="main-content">
        {error && (
          <div className="error-banner">
            <span>⚠️</span>
            <span>Connection error: {error}</span>
            <button onClick={() => { refreshInventory(); refreshStats(); }}>Retry</button>
          </div>
        )}
        
        {activeTab === 'dashboard' && (
          <Dashboard 
            stats={stats} 
            inventory={inventory} 
            onRefresh={refreshInventory} 
            onFeedback={setFeedback} 
          />
        )}
        {activeTab === 'voice' && (
          <VoiceAssistant 
            onFeedback={setFeedback} 
            onSuccess={() => { 
              refreshInventory(); 
              refreshStats(); 
            }} 
          />
        )}
        {activeTab === 'camera' && (
          <CameraDetector 
            onFeedback={setFeedback} 
            onSuccess={() => { 
              refreshInventory(); 
              refreshStats(); 
            }} 
          />
        )}
      </div>

      <InventoryList 
        inventory={inventory} 
        onFeedback={setFeedback}
        onSuccess={() => { 
          refreshInventory(); 
          refreshStats(); 
        }}
      />
      <FeedbackMessage message={feedback} />
    </div>
  )
}

export default App