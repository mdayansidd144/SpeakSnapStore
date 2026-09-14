import { useState, useEffect, useCallback } from 'react'
import VoiceAssistant from './components/VoiceAssistant'
import CameraDetector from './components/CameraDetector'
import InventoryList from './components/InventoryList'
import FeedbackMessage from './components/FeedbackMessage'
import Dashboard from './components/Dashboard'

const API_BASE =
  import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [inventory, setInventory] = useState([])
  const [feedback, setFeedback] = useState('')
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    document.body.style.margin = '0'
    document.body.style.background = '#C7E2F2'
    document.body.style.fontFamily =
      'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'

    return () => {
      document.body.style.margin = ''
      document.body.style.background = ''
      document.body.style.fontFamily = ''
    }
  }, [])

  const refreshInventory = useCallback(async () => {
    try {
      setLoading(true)

      const response = await fetch(
        `${API_BASE}/api/inventory/`
      )

      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}: ${response.statusText}`
        )
      }

      const data = await response.json()

      setInventory(
        Array.isArray(data) ? data : []
      )

      setError(null)
    } catch (err) {
      console.error(
        'Failed to fetch inventory:',
        err
      )

      setError(
        err.message || 'Unable to connect to the backend.'
      )

      setInventory([])
    } finally {
      setLoading(false)
    }
  }, [])

  const refreshStats = useCallback(async () => {
    try {
      const response = await fetch(
        `${API_BASE}/api/inventory/stats`
      )

      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}: ${response.statusText}`
        )
      }

      const data = await response.json()

      setStats(data)
    } catch (err) {
      console.error(
        'Failed to fetch statistics:',
        err
      )

      setStats({
        total_items: 0,
        total_quantity: 0,
        total_value: 0,
        low_stock_items: 0
      })
    }
  }, [])

  const refreshAll = useCallback(async () => {
    await Promise.all([
      refreshInventory(),
      refreshStats()
    ])
  }, [
    refreshInventory,
    refreshStats
  ])

  useEffect(() => {
    refreshAll()
  }, [refreshAll])

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    setFeedback('')
  }

  const handleSuccess = async () => {
    await refreshAll()
  }

  const renderContent = () => {
    if (activeTab === 'dashboard') {
      return (
        <Dashboard
          stats={stats}
          inventory={inventory}
          onRefresh={refreshInventory}
          onFeedback={setFeedback}
        />
      )
    }

    if (activeTab === 'voice') {
      return (
        <VoiceAssistant
          onFeedback={setFeedback}
          onSuccess={handleSuccess}
        />
      )
    }

    if (activeTab === 'camera') {
      return (
        <CameraDetector
          onFeedback={setFeedback}
          onSuccess={handleSuccess}
        />
      )
    }

    return null
  }

  const navButtonStyle = (tab) => ({
    flex: 1,
    minWidth: '120px',
    height: '42px',
    border:
      activeTab === tab
        ? '1px solid #005A9E'
        : '1px solid #C5DDEB',
    borderRadius: '8px',
    background:
      activeTab === tab
        ? '#005A9E'
        : '#FFFFFF',
    color:
      activeTab === tab
        ? '#FFFFFF'
        : '#12344A',
    fontFamily: 'inherit',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background 0.15s ease'
  })

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#C7E2F2',
        color: '#12344A'
      }}
    >
      <header
        style={{
          background: '#E7F3FB',
          borderBottom: '1px solid #B8D5E5'
        }}
      >
        <div
          style={{
            width: 'min(1180px, calc(100% - 32px))',
            margin: '0 auto',
            padding: '24px 0 20px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '20px',
            flexWrap: 'wrap'
          }}
        >
          <div>
            <h1
              style={{
                margin: 0,
                color: '#004578',
                fontSize: '27px',
                lineHeight: 1.15,
                fontWeight: 750,
                letterSpacing: '-0.5px'
              }}
            >
              Speak Snap Store
            </h1>

            <p
              style={{
                margin: '7px 0 0',
                color: '#47687D',
                fontSize: '13px',
                lineHeight: 1.5
              }}
            >
              Voice, vision and intelligent inventory management
            </p>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 12px',
              background: '#FFFFFF',
              border: '1px solid #C5DDEB',
              borderRadius: '8px',
              color: '#365E74',
              fontSize: '12px',
              fontWeight: 600
            }}
          >
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: loading
                  ? '#D97706'
                  : '#16803C'
              }}
            />

            {loading
              ? 'Syncing'
              : 'System ready'}
          </div>
        </div>
      </header>

      <main
        style={{
          width: 'min(1180px, calc(100% - 32px))',
          margin: '0 auto',
          padding: '18px 0 40px'
        }}
      >
        <nav
          style={{
            display: 'flex',
            gap: '8px',
            padding: '6px',
            marginBottom: '22px',
            background: '#E7F3FB',
            border: '1px solid #B8D5E5',
            borderRadius: '10px'
          }}
        >
          <button
            type="button"
            onClick={() =>
              handleTabChange('dashboard')
            }
            style={navButtonStyle('dashboard')}
          >
            Dashboard
          </button>

          <button
            type="button"
            onClick={() =>
              handleTabChange('voice')
            }
            style={navButtonStyle('voice')}
          >
            Voice Assistant
          </button>

          <button
            type="button"
            onClick={() =>
              handleTabChange('camera')
            }
            style={navButtonStyle('camera')}
          >
            Camera Detection
          </button>
        </nav>

        {error && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '14px',
              padding: '13px 16px',
              marginBottom: '20px',
              background: '#FFF4F2',
              border: '1px solid #F0B8B0',
              borderLeft: '4px solid #C24135',
              borderRadius: '8px',
              color: '#8B2E26',
              fontSize: '13px'
            }}
          >
            <span>
              Connection error: {error}
            </span>

            <button
              type="button"
              onClick={refreshAll}
              disabled={loading}
              style={{
                height: '34px',
                padding: '0 13px',
                border: '1px solid #C24135',
                borderRadius: '6px',
                background: '#FFFFFF',
                color: '#8B2E26',
                fontFamily: 'inherit',
                fontSize: '12px',
                fontWeight: 600,
                cursor: loading
                  ? 'not-allowed'
                  : 'pointer'
              }}
            >
              Retry
            </button>
          </div>
        )}

        {renderContent()}

        <section
          style={{
            marginTop: '22px'
          }}
        >
          <InventoryList
            inventory={inventory}
            onFeedback={setFeedback}
            onSuccess={handleSuccess}
          />
        </section>
      </main>

      <FeedbackMessage message={feedback} />
    </div>
  )
}

export default App