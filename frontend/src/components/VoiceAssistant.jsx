import { useState, useRef, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function VoiceAssistant({ onFeedback, onSuccess }) {
  const [input, setInput] = useState('')
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [multipleItems, setMultipleItems] = useState(null)
  const recognitionRef = useRef(null)

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort()
      }
    }
  }, [])

  const parseMultipleItems = (text) => {
    const items = []
    const pattern = /(\d+)\s+([a-zA-Z\s]+?)(?=,|$|and|\.)/g
    let match
    const tempText = text.replace(/add/gi, '').replace(/stock/gi, '').trim()
    
    while ((match = pattern.exec(tempText)) !== null) {
      const quantity = parseInt(match[1])
      let itemName = match[2].trim().replace(/,/g, '').trim()
      if (itemName && quantity > 0 && itemName.length > 1) {
        items.push({ item: itemName, quantity, action: 'add' })
      }
    }
    return items
  }

  const startVoice = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      onFeedback('❌ Voice recognition not supported')
      return
    }

    const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition
    const recognition = new SpeechRecognition()
    recognitionRef.current = recognition
    
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-US'

    recognition.onstart = () => {
      setIsListening(true)
      onFeedback('🎤 Listening...')
    }

    recognition.onresult = (event) => {
      const text = event.results[0][0].transcript
      setInput(text)
      onFeedback(`🗣️ "${text}"`)
      parseCommand(text)
      setIsListening(false)
    }

    recognition.onerror = () => {
      onFeedback('❌ Could not hear you')
      setIsListening(false)
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognition.start()
  }

  const stopVoice = () => {
    if (recognitionRef.current) {
      recognitionRef.current.abort()
      setIsListening(false)
      onFeedback('🎤 Stopped')
    }
  }

  const parseCommand = async (text) => {
    if (!text || !text.trim()) {
      onFeedback('❌ Please enter a command')
      return
    }
    
    setLoading(true)
    onFeedback('🤔 Processing...')
    setMultipleItems(null)
    setPreview(null)
    
    const hasMultiple = (text.match(/,/g) || []).length > 0 || (text.match(/and/g) || []).length > 0
    const multipleItemsMatch = parseMultipleItems(text)
    
    if (hasMultiple && multipleItemsMatch.length > 1) {
      setMultipleItems(multipleItemsMatch)
      onFeedback(`✅ Found ${multipleItemsMatch.length} items!`)
      setLoading(false)
      return
    }
    
    try {
      const response = await fetch(`${API_BASE}/api/parse/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim() })
      })
      
      if (!response.ok) throw new Error('Parse failed')
      
      const data = await response.json()
      
      if (!data.item || data.item === 'item') {
        onFeedback('❌ Could not identify item')
        setLoading(false)
        return
      }
      
      if (!data.quantity || data.quantity <= 0) {
        onFeedback('❌ Could not identify quantity')
        setLoading(false)
        return
      }
      
      setPreview(data)
      onFeedback(`✅ ${data.quantity} × ${data.item}`)
    } catch (error) {
      onFeedback('❌ Command not recognized')
    }
    setLoading(false)
  }

  const confirmAction = async () => {
    if (!preview) return
    
    const endpoint = preview.action === 'add' ? '/api/inventory/add' : '/api/inventory/remove'
    
    onFeedback(`⏳ ${preview.action === 'add' ? 'Adding' : 'Removing'} ${preview.quantity} × ${preview.item}...`)
    
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          name: preview.item.toLowerCase(), 
          quantity: preview.quantity 
        })
      })
      
      if (!response.ok) throw new Error('Failed')
      
      const data = await response.json()
      onFeedback(`🎉 ${data.message}`)
      setPreview(null)
      setInput('')
      onSuccess()
    } catch (error) {
      onFeedback(`❌ Failed to update`)
    }
  }

  const confirmMultipleItems = async () => {
    if (!multipleItems) return
    
    onFeedback(`⏳ Adding ${multipleItems.length} items...`)
    
    let successCount = 0
    for (const item of multipleItems) {
      try {
        const response = await fetch(`${API_BASE}/api/inventory/add`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            name: item.item.toLowerCase(), 
            quantity: item.quantity 
          })
        })
        if (response.ok) successCount++
      } catch (error) {
        console.error(`Failed to add ${item.item}:`, error)
      }
    }
    
    onFeedback(`✅ Added ${successCount}/${multipleItems.length} items!`)
    setMultipleItems(null)
    setInput('')
    onSuccess()
  }

  const cancelMultipleItems = () => {
    setMultipleItems(null)
    onFeedback('❌ Cancelled')
  }

  const cancelAction = () => {
    setPreview(null)
    onFeedback('Cancelled')
  }

  const exampleCommands = [
    { text: 'add 5 apples', icon: '🍎', color: '#4CAF50' },
    { text: 'remove 2 oranges', icon: '🍊', color: '#FF9800' },
    { text: 'add 10 biscuits', icon: '🍪', color: '#2196F3' },
    { text: '10 biscuits, 10 books, 2 chocolates', icon: '📦', color: '#9C27B0' }
  ]

  return (
    <div className="voice-assistant" style={styles.container}>
      {/* Voice Button */}
      <div style={styles.micSection}>
        <button 
          className={`mic-button ${isListening ? 'listening' : ''}`}
          onClick={isListening ? stopVoice : startVoice}
          style={styles.micButton(isListening)}
        >
          <div style={styles.micIcon}>{isListening ? '🔴' : '🎤'}</div>
          <span style={styles.micText}>
            {isListening ? 'Listening...' : 'Click to Speak'}
          </span>
        </button>
        <p style={styles.micHint}>
          Try: <strong>"10 biscuits, 10 books, 2 chocolates"</strong>
        </p>
      </div>

      {/* Input Area */}
      <div style={styles.inputSection}>
        <div style={styles.inputWrapper}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder='Type: "10 biscuits, 10 books, 2 chocolates"'
            style={styles.input}
            onKeyPress={(e) => e.key === 'Enter' && parseCommand(input)}
          />
          <button 
            onClick={() => parseCommand(input)} 
            disabled={loading || !input.trim()}
            style={styles.parseButton(loading || !input.trim())}
          >
            {loading ? '⟳' : 'Parse'}
          </button>
        </div>
      </div>

      {/* Example Commands */}
      <div style={styles.examplesSection}>
        <p style={styles.examplesTitle}>💡 Try these commands:</p>
        <div style={styles.examplesGrid}>
          {exampleCommands.map((cmd, i) => (
            <button
              key={i}
              onClick={() => {
                setInput(cmd.text)
                parseCommand(cmd.text)
              }}
              style={styles.exampleButton(cmd.color)}
            >
              <span style={{ marginRight: '6px' }}>{cmd.icon}</span>
              <span>{cmd.text.length > 35 ? cmd.text.substring(0, 35) + '...' : cmd.text}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Multiple Items Preview */}
      {multipleItems && (
        <div style={styles.multiplePreview}>
          <h3 style={styles.multipleTitle}>📦 Multiple Items Detected</h3>
          <div style={styles.multipleList}>
            {multipleItems.map((item, idx) => (
              <div key={idx} style={styles.multipleItem}>
                <span style={{ textTransform: 'capitalize', fontWeight: '500' }}>{item.item}</span>
                <span style={styles.multipleItemBadge}>{item.quantity} units</span>
              </div>
            ))}
          </div>
          <div style={styles.previewActions}>
            <button onClick={confirmMultipleItems} style={styles.confirmButton}>
              ✅ Add All
            </button>
            <button onClick={cancelMultipleItems} style={styles.cancelButton}>
              ❌ Cancel
            </button>
          </div>
        </div>
      )}

      {/* Single Item Preview */}
      {preview && (
        <div style={styles.singlePreview}>
          <h3 style={styles.singleTitle}>📋 Preview</h3>
          <p style={styles.previewQuantity}>
            {preview.quantity} × {preview.item}
          </p>
          <div style={styles.previewActions}>
            <button onClick={confirmAction} style={styles.confirmButton}>
              ✅ Confirm
            </button>
            <button onClick={cancelAction} style={styles.cancelButton}>
              ❌ Cancel
            </button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(102, 126, 234, 0.4); }
          70% { transform: scale(1.05); box-shadow: 0 0 0 15px rgba(102, 126, 234, 0); }
          100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(102, 126, 234, 0); }
        }
        
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(-20px); }
          to { opacity: 1; transform: translateX(0); }
        }
        
        .mic-button {
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .mic-button:hover {
          transform: scale(1.02);
        }
        
        .mic-button:active {
          transform: scale(0.98);
          transition: transform 0.05s;
        }
        
        .voice-assistant {
          animation: fadeIn 0.3s ease;
        }
      `}</style>
    </div>
  )
}

const styles = {
  container: {
    padding: '24px',
    background: 'linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%)',
    borderRadius: '28px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.06)',
    border: '1px solid rgba(102, 126, 234, 0.15)',
    animation: 'fadeIn 0.3s ease'
  },
  micSection: {
    textAlign: 'center',
    marginBottom: '28px'
  },
  micButton: (isListening) => ({
    width: '140px',
    height: '140px',
    borderRadius: '50%',
    background: isListening ? '#ff4444' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    border: 'none',
    cursor: 'pointer',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    margin: '0 auto',
    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
    boxShadow: isListening ? '0 0 25px rgba(255,68,68,0.5)' : '0 8px 25px rgba(102,126,234,0.3)',
    animation: isListening ? 'pulse 1.5s infinite' : 'none'
  }),
  micIcon: {
    fontSize: '52px'
  },
  micText: {
    fontSize: '13px',
    color: 'white',
    fontWeight: '600'
  },
  micHint: {
    fontSize: '13px',
    color: '#5a6e6c',
    marginTop: '12px'
  },
  inputSection: {
    marginBottom: '24px'
  },
  inputWrapper: {
    display: 'flex',
    gap: '10px',
    background: 'white',
    borderRadius: '60px',
    padding: '6px',
    border: '1px solid rgba(102, 126, 234, 0.2)',
    transition: 'all 0.2s',
    boxShadow: '0 2px 8px rgba(0,0,0,0.02)'
  },
  input: {
    flex: 1,
    padding: '14px 20px',
    fontSize: '14px',
    border: 'none',
    background: 'transparent',
    outline: 'none',
    fontFamily: 'inherit'
  },
  parseButton: (disabled) => ({
    padding: '12px 28px',
    fontSize: '14px',
    background: disabled ? '#ccc' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '50px',
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontWeight: '600',
    transition: 'all 0.2s'
  }),
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
  exampleButton: (color) => ({
    padding: '8px 16px',
    fontSize: '12px',
    background: 'white',
    border: `1px solid ${color}20`,
    borderRadius: '40px',
    cursor: 'pointer',
    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    color: color,
    fontWeight: '500'
  }),
  multiplePreview: {
    marginTop: '20px',
    padding: '20px',
    background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)',
    borderRadius: '20px',
    animation: 'slideIn 0.3s ease',
    border: '1px solid #a5d6a7'
  },
  multipleTitle: {
    margin: '0 0 12px 0',
    color: '#2e7d32',
    fontSize: '1rem',
    fontWeight: '600'
  },
  multipleList: {
    marginBottom: '16px',
    maxHeight: '200px',
    overflowY: 'auto'
  },
  multipleItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 0',
    borderBottom: '1px solid rgba(0,0,0,0.08)'
  },
  multipleItemBadge: {
    background: '#4CAF50',
    color: 'white',
    padding: '2px 12px',
    borderRadius: '20px',
    fontSize: '12px'
  },
  singlePreview: {
    marginTop: '20px',
    padding: '20px',
    background: 'linear-gradient(135deg, #fff8e7 0%, #fff3e0 100%)',
    borderRadius: '20px',
    animation: 'slideIn 0.3s ease',
    border: '1px solid #ffe0b2'
  },
  singleTitle: {
    margin: '0 0 12px 0',
    color: '#e65100',
    fontSize: '1rem',
    fontWeight: '600'
  },
  previewQuantity: {
    fontSize: '28px',
    margin: '10px 0',
    fontWeight: 'bold',
    textAlign: 'center',
    color: '#667eea'
  },
  previewActions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'center',
    marginTop: '16px'
  },
  confirmButton: {
    padding: '10px 24px',
    fontSize: '14px',
    fontWeight: '600',
    background: 'linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '40px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    boxShadow: '0 2px 8px rgba(76, 175, 80, 0.3)'
  },
  cancelButton: {
    padding: '10px 24px',
    fontSize: '14px',
    fontWeight: '600',
    background: 'linear-gradient(135deg, #f44336 0%, #d32f2f 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '40px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    boxShadow: '0 2px 8px rgba(244, 67, 54, 0.3)'
  }
}