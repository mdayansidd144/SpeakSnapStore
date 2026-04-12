

import { useState, useEffect } from 'react'
import VoiceAssistant from './components/VoiceAssistant'
import CameraDetector from './components/CameraDetector'
import InventoryList from './components/InventoryList'
import FeedbackMessage from './components/FeedbackMessage'
import Dashboard from './components/Dashboard'
import './App.css'

const API_BASE = 'http://localhost:8000'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [inventory, setInventory] = useState([])
  const [feedback, setFeedback] = useState('')
  const [stats, setStats] = useState(null)

  const refreshInventory = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/inventory/`)
      if (!res.ok) throw new Error('Failed to fetch')
      const data = await res.json()
      setInventory(data)
    } catch (error) {
      console.error('Failed to fetch inventory:', error)
      setInventory([])
    }
  }

  const refreshStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/inventory/stats`)
      if (!res.ok) throw new Error('Failed to fetch')
      const data = await res.json()
      setStats(data)
    } catch (error) {
      console.error('Failed to fetch stats:', error)
      setStats({ total_items: 0, total_quantity: 0, total_value: 0 })
    }
  }

  useEffect(() => {
    refreshInventory()
    refreshStats()
  }, [])

  // Dynamic gradient based on active tab
  const getBackgroundGradient = () => {
    switch(activeTab) {
      case 'dashboard':
        return 'linear-gradient(135deg, #e8f4f8 0%, #d1eef5 50%, #b8e5f0 100%)'
      case 'voice':
        return 'linear-gradient(135deg, #e8f8f0 0%, #d0f0e0 50%, #b8e8d0 100%)'
      case 'camera':
        return 'linear-gradient(135deg, #fff5e8 0%, #ffeed5 50%, #ffe5c0 100%)'
      default:
        return 'linear-gradient(135deg, #e8f4f8 0%, #d1eef5 50%, #b8e5f0 100%)'
    }
  }

  return (
    <div className="app" style={{ background: getBackgroundGradient() }}>
      <header className="app-header">
        <div className="logo">
          <span className="logo-icon">📦</span>
          <span className="logo-text"> Speak Snap Stock</span>
        </div>
        <p className="tagline">AI-Powered Inventory Manager</p>
      </header>

      <nav className="bottom-nav">
        <button 
          className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          <span className="nav-icon">📊</span>
          <span className="nav-label">Dashboard</span>
        </button>
        <button 
          className={`nav-item ${activeTab === 'voice' ? 'active' : ''}`}
          onClick={() => setActiveTab('voice')}
        >
          <span className="nav-icon">🎤</span>
          <span className="nav-label">Voice</span>
        </button>
        <button 
          className={`nav-item ${activeTab === 'camera' ? 'active' : ''}`}
          onClick={() => setActiveTab('camera')}
        >
          <span className="nav-icon">📸</span>
          <span className="nav-label">Camera</span>
        </button>
      </nav>

      <main className="main-content">
        {activeTab === 'dashboard' && <Dashboard stats={stats} inventory={inventory} onRefresh={refreshInventory} onFeedback={setFeedback} />}
        {activeTab === 'voice' && <VoiceAssistant onFeedback={setFeedback} onSuccess={() => { refreshInventory(); refreshStats(); }} />}
        {activeTab === 'camera' && <CameraDetector onFeedback={setFeedback} onSuccess={() => { refreshInventory(); refreshStats(); }} />}
      </main>

      <InventoryList 
        inventory={inventory} 
        onFeedback={setFeedback}
        onSuccess={() => { refreshInventory(); refreshStats(); }}
      />
      <FeedbackMessage message={feedback} />
    </div>
  )
}

export default App