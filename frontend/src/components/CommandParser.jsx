import { useState, useCallback, useEffect, useRef } from 'react'
export default function CommandParser({ onParsed, onFeedback, onLoading, onSuccess }) {
  const [input, setInput] = useState('')
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const inputRef = useRef(null)

  // Load history from localStorage on mount
  useEffect(() => {
    const savedHistory = localStorage.getItem('commandHistory')
    if (savedHistory) {
      try {
        setHistory(JSON.parse(savedHistory))
      } catch (e) {
        console.error('Failed to load history')
      }
    }
    inputRef.current?.focus()
  }, [])

  // Save history to localStorage
  const saveToHistory = useCallback((command) => {
    setHistory(prev => {
      const newHistory = [command, ...prev.filter(c => c !== command)].slice(0, 20)
      localStorage.setItem('commandHistory', JSON.stringify(newHistory))
      return newHistory
    })
    setHistoryIndex(-1)
  }, [])

  // Parse command using your backend API
  const parseCommand = useCallback(async (text) => {
    if (!text || !text.trim()) {
      onFeedback?.('❌ Please enter a command')
      return null
    }

    setLoading(true)
    onLoading?.(true)
    onFeedback?.('🤔 Processing your command...')

    try {
      const response = await fetch('/api/parse/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: text.trim() })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Parse failed')
      }

      const data = await response.json()

      // Validate response from your parse.py
      if (!data.item || data.item === 'item' || data.item === '') {
        onFeedback?.('❌ Could not identify the item. Try "add 5 apples"')
        setLoading(false)
        onLoading?.(false)
        return null
      }

      if (!data.quantity || data.quantity <= 0) {
        onFeedback?.('❌ Could not identify quantity. Try "add 5 apples"')
        setLoading(false)
        onLoading?.(false)
        return null
      }

      if (!data.action || (data.action !== 'add' && data.action !== 'remove')) {
        onFeedback?.('❌ Could not identify action (add/remove). Try "add 5 apples"')
        setLoading(false)
        onLoading?.(false)
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
      console.error('Parse error:', error)
      onFeedback?.(`❌ ${error.message || 'Error parsing command. Try "add 5 apples"'}`)
      return null
    } finally {
      setLoading(false)
      onLoading?.(false)
    }
  }, [onFeedback, onParsed, onLoading])

  // Confirm action (add/remove) - matches your inventory endpoints
  const confirmAction = useCallback(async () => {
    if (!preview) return

    const endpoint = preview.action === 'add' ? '/api/inventory/add' : '/api/inventory/remove'
    
    setLoading(true)
    onLoading?.(true)
    onFeedback?.(`📦 ${preview.action === 'add' ? 'Adding' : 'Removing'} ${preview.quantity} × ${preview.item}...`)

    try {
      const response = await fetch(endpoint, {
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
      
      // Save to history only on successful action
      saveToHistory(preview.originalText)
      
      // Clear preview and input after successful action
      setPreview(null)
      setInput('')
      
      // Call success callback to refresh inventory
      onSuccess?.()
      
      return data

    } catch (error) {
      console.error('Confirm error:', error)
      onFeedback?.(`❌ ${error.message || 'Failed to update inventory'}`)
      return null
    } finally {
      setLoading(false)
      onLoading?.(false)
    }
  }, [preview, onFeedback, onLoading, saveToHistory, onSuccess])

  // Cancel preview
  const cancelAction = useCallback(() => {
    setPreview(null)
    onFeedback?.('❌ Action cancelled')
  }, [onFeedback])

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e) => {
    // Enter key to parse
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      parseCommand(input)
    }
    // Up arrow for history (previous command)
    else if (e.key === 'ArrowUp' && history.length > 0) {
      e.preventDefault()
      const newIndex = historyIndex + 1
      if (newIndex < history.length) {
        setHistoryIndex(newIndex)
        setInput(history[newIndex])
      }
    }
    // Down arrow for history (next command)
    else if (e.key === 'ArrowDown' && historyIndex > -1) {
      e.preventDefault()
      const newIndex = historyIndex - 1
      if (newIndex >= -1) {
        setHistoryIndex(newIndex)
        setInput(newIndex === -1 ? '' : history[newIndex])
      }
    }
  }, [input, history, historyIndex, parseCommand])

  // Quick insert example
  const insertExample = (text) => {
    setInput(text)
    parseCommand(text)
  }

  // Clear history
  const clearHistory = () => {
    setHistory([])
    localStorage.removeItem('commandHistory')
    onFeedback?.('🗑️ Command history cleared')
  }

  // Example commands that work with your parse.py
  const exampleCommands = [
    { text: 'add 5 apples', desc: 'Add 5 apples' },
    { text: 'remove 2 oranges', desc: 'Remove 2 oranges' },
    { text: 'add 10 biscuits', desc: 'Add 10 biscuits' },
    { text: 'remove 3 namkeen', desc: 'Remove 3 namkeen' },
    { text: 'stock 20 pencils', desc: 'Add 20 pencils' },
    { text: 'delete 1 mango', desc: 'Remove 1 mango' },
    { text: 'add five bananas', desc: 'Add 5 bananas (word number)' },
    { text: 'remove ten chips', desc: 'Remove 10 chips (word number)' }
  ]

  return (
    <div style={styles.container}>
      {/* Input Area */}
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
            style={{
              ...styles.parseButton,
              opacity: (loading || !input.trim()) ? 0.6 : 1,
              cursor: (loading || !input.trim()) ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? '⏳ Parsing...' : '🔍 Parse'}
          </button>
        </div>
        
        {/* History hint */}
        {history.length > 0 && (
          <div style={styles.historyBar}>
            <span style={styles.historyHint}>
              ⬆️⬇️ Arrow keys: {history.length} commands in history
            </span>
            <button onClick={clearHistory} style={styles.clearHistoryBtn}>
              Clear
            </button>
          </div>
        )}
      </div>

      {/* Example Commands */}
      <div style={styles.examplesSection}>
        <p style={styles.examplesTitle}>💡 Try these commands:</p>
        <div style={styles.examplesGrid}>
          {exampleCommands.map((cmd, i) => (
            <button
              key={i}
              onClick={() => insertExample(cmd.text)}
              disabled={loading}
              style={styles.exampleButton}
              title={cmd.desc}
            >
              {cmd.text}
            </button>
          ))}
        </div>
      </div>

      {/* Preview Card - Shows parsed result before confirming */}
      {preview && (
        <div style={styles.previewCard}>
          <div style={styles.previewHeader}>
            <span>📋 Command Preview</span>
            <button onClick={cancelAction} style={styles.closeButton} title="Cancel">
              ✖
            </button>
          </div>
          
          <div style={styles.previewContent}>
            <div style={styles.previewRow}>
              <span style={styles.previewLabel}>Command:</span>
              <span style={styles.previewCommand}>"{preview.originalText}"</span>
            </div>
            <div style={styles.previewRow}>
              <span style={styles.previewLabel}>Action:</span>
              <span style={{
                ...styles.actionBadge,
                backgroundColor: preview.action === 'add' ? '#4CAF50' : '#f44336'
              }}>
                {preview.action === 'add' ? '➕ ADD' : '➖ REMOVE'}
              </span>
            </div>
            <div style={styles.previewRow}>
              <span style={styles.previewLabel}>Quantity:</span>
              <span style={styles.previewValue}>
                <strong>{preview.quantity}</strong>
              </span>
            </div>
            <div style={styles.previewRow}>
              <span style={styles.previewLabel}>Item:</span>
              <span style={styles.previewValue}>
                <strong>{preview.item}</strong>
              </span>
            </div>
          </div>
          
          <div style={styles.previewActions}>
            <button
              onClick={confirmAction}
              disabled={loading}
              style={styles.confirmButton}
              onMouseEnter={(e) => e.target.style.transform = 'scale(1.02)'}
              onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
            >
              {loading ? '⏳ Processing...' : '✅ Confirm'}
            </button>
            <button
              onClick={cancelAction}
              disabled={loading}
              style={styles.cancelButton}
              onMouseEnter={(e) => e.target.style.transform = 'scale(1.02)'}
              onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
            >
              ❌ Cancel
            </button>
          </div>
        </div>
      )}

      {/* Loading Overlay */}
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
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(-20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  )
}

const styles = {
  container: {
    position: 'relative',
    width: '100%',
    maxWidth: '750px',
    margin: '0 auto',
    padding: '24px',
    background: 'white',
    borderRadius: '20px',
    boxShadow: '0 8px 30px rgba(0,0,0,0.12)'
  },
  inputArea: {
    marginBottom: '20px'
  },
  inputWrapper: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center'
  },
  input: {
    flex: 1,
    padding: '14px 18px',
    fontSize: '15px',
    border: '2px solid #e9ecef',
    borderRadius: '12px',
    outline: 'none',
    transition: 'all 0.3s',
    fontFamily: 'inherit',
    backgroundColor: '#f8f9fa'
  },
  parseButton: {
    padding: '14px 28px',
    fontSize: '15px',
    fontWeight: '600',
    background: '#2196F3',
    color: 'white',
    border: 'none',
    borderRadius: '12px',
    transition: 'all 0.3s'
  },
  historyBar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '8px',
    padding: '0 4px'
  },
  historyHint: {
    fontSize: '11px',
    color: '#adb5bd'
  },
  clearHistoryBtn: {
    fontSize: '10px',
    background: 'none',
    border: 'none',
    color: '#adb5bd',
    cursor: 'pointer',
    padding: '2px 8px',
    borderRadius: '10px'
  },
  examplesSection: {
    marginBottom: '20px',
    padding: '16px',
    background: '#f8f9fa',
    borderRadius: '14px'
  },
  examplesTitle: {
    fontSize: '12px',
    color: '#6c757d',
    marginBottom: '12px',
    marginTop: 0,
    fontWeight: '500'
  },
  examplesGrid: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap'
  },
  exampleButton: {
    padding: '6px 14px',
    fontSize: '12px',
    background: 'white',
    border: '1px solid #dee2e6',
    borderRadius: '20px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    color: '#495057'
  },
  previewCard: {
    marginTop: '20px',
    padding: '20px',
    background: 'linear-gradient(135deg, #fff8e7 0%, #fff3e0 100%)',
    borderRadius: '16px',
    animation: 'slideIn 0.3s ease',
    border: '1px solid #ffe0b2'
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
    fontSize: '16px',
    cursor: 'pointer',
    color: '#999',
    padding: '4px 8px',
    borderRadius: '20px',
    transition: 'background 0.2s'
  },
  previewContent: {
    marginBottom: '20px'
  },
  previewRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
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
    background: '#4CAF50',
    color: 'white',
    border: 'none',
    borderRadius: '10px',
    cursor: 'pointer',
    transition: 'transform 0.2s'
  },
  cancelButton: {
    padding: '10px 28px',
    fontSize: '14px',
    fontWeight: '600',
    background: '#f44336',
    color: 'white',
    border: 'none',
    borderRadius: '10px',
    cursor: 'pointer',
    transition: 'transform 0.2s'
  },
  loadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(255,255,255,0.95)',
    borderRadius: '20px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    zIndex: 10
  },
  loadingSpinner: {
    width: '40px',
    height: '40px',
    border: '3px solid #e9ecef',
    borderTop: '3px solid #2196F3',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite'
  },
  loadingText: {
    fontSize: '14px',
    color: '#6c757d'
  }
}