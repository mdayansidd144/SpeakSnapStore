import { useState, useCallback, useEffect, useRef } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function CommandParser({ onParsed, onFeedback, onLoading, onSuccess }) {
  const [input, setInput] = useState('')
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const inputRef = useRef(null)

  useEffect(() => {
    const savedHistory = localStorage.getItem('commandHistory')
    if (savedHistory) {
      try {
        setHistory(JSON.parse(savedHistory))
      } catch (e) {}
    }
    inputRef.current?.focus()
  }, [])

  const saveToHistory = useCallback((command) => {
    setHistory(prev => {
      const newHistory = [command, ...prev.filter(c => c !== command)].slice(0, 20)
      localStorage.setItem('commandHistory', JSON.stringify(newHistory))
      return newHistory
    })
    setHistoryIndex(-1)
  }, [])

  const parseCommand = useCallback(async (text) => {
    if (!text || !text.trim()) {
      onFeedback?.('❌ Please enter a command')
      return null
    }

    setLoading(true)
    onLoading?.(true)
    onFeedback?.('🤔 Processing your command...')

    try {
      const response = await fetch(`${API_BASE}/api/parse/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim() })
      })

      if (!response.ok) {
        throw new Error('Parse failed')
      }

      const data = await response.json()

      if (!data.item || data.item === 'item') {
        onFeedback?.('❌ Could not identify the item. Try "add 5 apples"')
        return null
      }

      if (!data.quantity || data.quantity <= 0) {
        onFeedback?.('❌ Could not identify quantity')
        return null
      }

      const parsedData = {
        item: data.item,
        quantity: data.quantity,
        action: data.action,
        originalText: text
      }

      setPreview(parsedData)
      onParsed?.(parsedData)
      onFeedback?.(`✅ Parsed: ${data.action} ${data.quantity} × ${data.item}`)
      
      return parsedData
    } catch (error) {
      onFeedback?.(`❌ ${error.message || 'Error parsing command'}`)
      return null
    } finally {
      setLoading(false)
      onLoading?.(false)
    }
  }, [onFeedback, onParsed, onLoading])

  const confirmAction = useCallback(async () => {
    if (!preview) return

    const endpoint = preview.action === 'add' ? '/api/inventory/add' : '/api/inventory/remove'
    
    setLoading(true)
    onLoading?.(true)
    onFeedback?.(`📦 ${preview.action === 'add' ? 'Adding' : 'Removing'} ${preview.quantity} × ${preview.item}...`)

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          name: preview.item.toLowerCase(), 
          quantity: preview.quantity 
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Operation failed')
      }

      const data = await response.json()
      onFeedback?.(`🎉 ${data.message}`)
      saveToHistory(preview.originalText)
      setPreview(null)
      setInput('')
      onSuccess?.()
      
      return data
    } catch (error) {
      onFeedback?.(`❌ ${error.message || 'Failed to update inventory'}`)
      return null
    } finally {
      setLoading(false)
      onLoading?.(false)
    }
  }, [preview, onFeedback, onLoading, saveToHistory, onSuccess])

  const cancelAction = useCallback(() => {
    setPreview(null)
    onFeedback?.('❌ Action cancelled')
  }, [onFeedback])

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      parseCommand(input)
    } else if (e.key === 'ArrowUp' && history.length > 0) {
      e.preventDefault()
      const newIndex = historyIndex + 1
      if (newIndex < history.length) {
        setHistoryIndex(newIndex)
        setInput(history[newIndex])
      }
    } else if (e.key === 'ArrowDown' && historyIndex > -1) {
      e.preventDefault()
      const newIndex = historyIndex - 1
      if (newIndex >= -1) {
        setHistoryIndex(newIndex)
        setInput(newIndex === -1 ? '' : history[newIndex])
      }
    }
  }, [input, history, historyIndex, parseCommand])

  const insertExample = (text) => {
    setInput(text)
    parseCommand(text)
  }

  const clearHistory = () => {
    setHistory([])
    localStorage.removeItem('commandHistory')
    onFeedback?.('🗑️ Command history cleared')
  }

  const exampleCommands = [
    { text: 'add 5 apples', desc: 'Add 5 apples', icon: '🍎' },
    { text: 'remove 2 oranges', desc: 'Remove 2 oranges', icon: '🍊' },
    { text: 'add 10 biscuits', desc: 'Add 10 biscuits', icon: '🍪' },
    { text: '10 toothpaste, 10 water bottles, 15 notebooks', desc: 'Add multiple items', icon: '📦' }
  ]

  return (
    <div style={styles.container}>
      <div style={styles.inputArea}>
        <div style={styles.inputWrapper}>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder='Type a command... (e.g., "add 5 apples")'
            style={styles.input}
            disabled={loading}
          />
          <button
            onClick={() => parseCommand(input)}
            disabled={loading || !input.trim()}
            style={styles.parseButton}
          >
            {loading ? '⏳ Parsing...' : '🔍 Parse'}
          </button>
        </div>
        
        {history.length > 0 && (
          <div style={styles.historyBar}>
            <span style={styles.historyHint}>⬆️⬇️ Arrow keys: {history.length} commands</span>
            <button onClick={clearHistory} style={styles.clearHistoryBtn}>Clear</button>
          </div>
        )}
      </div>

      <div style={styles.examplesSection}>
        <p style={styles.examplesTitle}>💡 Try these commands:</p>
        <div style={styles.examplesGrid}>
          {exampleCommands.map((cmd, i) => (
            <button key={i} onClick={() => insertExample(cmd.text)} style={styles.exampleButton} title={cmd.desc}>
              <span style={{ marginRight: '6px' }}>{cmd.icon}</span>
              {cmd.text}
            </button>
          ))}
        </div>
      </div>

      {preview && (
        <div style={styles.previewCard}>
          <div style={styles.previewHeader}>
            <span>📋 Command Preview</span>
            <button onClick={cancelAction} style={styles.closeButton}>✖</button>
          </div>
          <div style={styles.previewContent}>
            <div style={styles.previewRow}>
              <span style={styles.previewLabel}>Command:</span>
              <span style={styles.previewCommand}>"{preview.originalText}"</span>
            </div>
            <div style={styles.previewRow}>
              <span style={styles.previewLabel}>Action:</span>
              <span style={{...styles.actionBadge, backgroundColor: preview.action === 'add' ? '#4CAF50' : '#f44336'}}>
                {preview.action === 'add' ? '➕ ADD' : '➖ REMOVE'}
              </span>
            </div>
            <div style={styles.previewRow}>
              <span style={styles.previewLabel}>Quantity:</span>
              <span style={styles.previewValue}><strong>{preview.quantity}</strong></span>
            </div>
            <div style={styles.previewRow}>
              <span style={styles.previewLabel}>Item:</span>
              <span style={styles.previewValue}><strong>{preview.item}</strong></span>
            </div>
          </div>
          <div style={styles.previewActions}>
            <button onClick={confirmAction} disabled={loading} style={styles.confirmButton}>
              {loading ? '⏳ Processing...' : '✅ Confirm'}
            </button>
            <button onClick={cancelAction} disabled={loading} style={styles.cancelButton}>
              ❌ Cancel
            </button>
          </div>
        </div>
      )}

      {loading && (
        <div style={styles.loadingOverlay}>
          <div style={styles.loadingSpinner}></div>
          <span style={styles.loadingText}>Processing...</span>
        </div>
      )}

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(-20px); }
          to { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </div>
  )
}

const styles = {
  container: {
    position: 'relative',
    width: '100%',
    maxWidth: '800px',
    margin: '0 auto',
    padding: '24px',
    background: 'linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%)',
    borderRadius: '28px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.08)',
    border: '1px solid rgba(102, 126, 234, 0.15)',
    animation: 'fadeIn 0.3s ease'
  },
  inputArea: { marginBottom: '24px' },
  inputWrapper: { 
    display: 'flex', 
    gap: '12px', 
    alignItems: 'center',
    background: 'white',
    borderRadius: '60px',
    padding: '4px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.03)',
    border: '1px solid rgba(102, 126, 234, 0.2)'
  },
  input: { 
    flex: 1, 
    padding: '14px 20px', 
    fontSize: '15px', 
    border: 'none', 
    borderRadius: '60px', 
    outline: 'none', 
    backgroundColor: 'transparent',
    fontFamily: 'inherit'
  },
  parseButton: { 
    padding: '12px 28px', 
    fontSize: '14px', 
    fontWeight: '600', 
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 
    color: 'white', 
    border: 'none', 
    borderRadius: '50px', 
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    boxShadow: '0 2px 8px rgba(102, 126, 234, 0.3)'
  },
  historyBar: { 
    display: 'flex', 
    justifyContent: 'space-between', 
    marginTop: '10px', 
    padding: '0 6px' 
  },
  historyHint: { 
    fontSize: '11px', 
    color: '#8a8a8e',
    background: '#f0f0f5',
    padding: '4px 12px',
    borderRadius: '20px'
  },
  clearHistoryBtn: { 
    fontSize: '11px', 
    background: 'none', 
    border: 'none', 
    color: '#f44336', 
    cursor: 'pointer',
    padding: '4px 12px',
    borderRadius: '20px',
    transition: 'all 0.2s'
  },
  examplesSection: { 
    marginBottom: '24px', 
    padding: '16px', 
    background: 'linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%)', 
    borderRadius: '20px',
    border: '1px solid rgba(102, 126, 234, 0.1)'
  },
  examplesTitle: { 
    fontSize: '12px', 
    color: '#667eea', 
    marginBottom: '12px', 
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  examplesGrid: { 
    display: 'flex', 
    gap: '10px', 
    flexWrap: 'wrap' 
  },
  exampleButton: { 
    padding: '8px 16px', 
    fontSize: '12px', 
    background: 'white', 
    border: '1px solid rgba(102, 126, 234, 0.2)', 
    borderRadius: '30px', 
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    color: '#333',
    fontWeight: '500'
  },
  previewCard: { 
    marginTop: '20px', 
    padding: '20px', 
    background: 'linear-gradient(135deg, #fff8e7 0%, #fff3e0 100%)', 
    borderRadius: '20px', 
    border: '1px solid #ffe0b2',
    animation: 'slideIn 0.3s ease'
  },
  previewHeader: { 
    display: 'flex', 
    justifyContent: 'space-between', 
    alignItems: 'center', 
    marginBottom: '16px', 
    fontSize: '15px', 
    fontWeight: '600', 
    color: '#e65100' 
  },
  closeButton: { 
    background: 'none', 
    border: 'none', 
    fontSize: '18px', 
    cursor: 'pointer', 
    color: '#999',
    padding: '4px 8px',
    borderRadius: '20px',
    transition: 'all 0.2s'
  },
  previewContent: { marginBottom: '20px' },
  previewRow: { 
    display: 'flex', 
    justifyContent: 'space-between', 
    padding: '10px 0', 
    borderBottom: '1px solid rgba(0,0,0,0.06)' 
  },
  previewLabel: { 
    fontSize: '13px', 
    color: '#856404', 
    fontWeight: '500' 
  },
  previewCommand: { 
    fontSize: '13px', 
    color: '#856404', 
    fontStyle: 'italic' 
  },
  previewValue: { 
    fontSize: '15px', 
    fontWeight: '600', 
    color: '#e65100' 
  },
  actionBadge: { 
    padding: '4px 14px', 
    borderRadius: '20px', 
    fontSize: '12px', 
    fontWeight: 'bold', 
    color: 'white' 
  },
  previewActions: { 
    display: 'flex', 
    gap: '12px', 
    justifyContent: 'center', 
    marginTop: '16px' 
  },
  confirmButton: { 
    padding: '10px 28px', 
    fontSize: '14px', 
    fontWeight: '600', 
    background: 'linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)', 
    color: 'white', 
    border: 'none', 
    borderRadius: '40px', 
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    boxShadow: '0 2px 8px rgba(76, 175, 80, 0.3)'
  },
  cancelButton: { 
    padding: '10px 28px', 
    fontSize: '14px', 
    fontWeight: '600', 
    background: 'linear-gradient(135deg, #f44336 0%, #d32f2f 100%)', 
    color: 'white', 
    border: 'none', 
    borderRadius: '40px', 
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    boxShadow: '0 2px 8px rgba(244, 67, 54, 0.3)'
  },
  loadingOverlay: { 
    position: 'absolute', 
    top: 0, 
    left: 0, 
    right: 0, 
    bottom: 0, 
    background: 'rgba(255,255,255,0.97)', 
    borderRadius: '28px', 
    display: 'flex', 
    flexDirection: 'column', 
    alignItems: 'center', 
    justifyContent: 'center', 
    gap: '16px', 
    zIndex: 10,
    backdropFilter: 'blur(4px)'
  },
  loadingSpinner: { 
    width: '48px', 
    height: '48px', 
    border: '3px solid #e9ecef', 
    borderTop: '3px solid #667eea', 
    borderRadius: '50%', 
    animation: 'spin 1s linear infinite' 
  },
  loadingText: { 
    fontSize: '14px', 
    color: '#667eea', 
    fontWeight: '500' 
  }
}