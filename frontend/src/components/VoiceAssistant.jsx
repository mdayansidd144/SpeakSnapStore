import { useState, useRef, useEffect } from 'react'
const API_BASE = 'http://localhost:8000'
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
      onFeedback('🎤 Listening... Speak your command')
    }

    recognition.onresult = (event) => {
      const text = event.results[0][0].transcript
      setInput(text)
      onFeedback(`🗣️ "${text}"`)
      parseCommand(text)
      setIsListening(false)
    }

    recognition.onerror = () => {
      onFeedback('❌ Could not hear you. Try typing.')
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
      onFeedback('🎤 Stopped listening')
    }
  }

  const parseCommand = async (text) => {
    if (!text || !text.trim()) {
      onFeedback('❌ Please enter a command')
      return
    }
    
    setLoading(true)
    onFeedback('🤔 Understanding your command...')
    setMultipleItems(null)
    setPreview(null)
    
    try {
      const response = await fetch(`${API_BASE}/api/parse/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim() })
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Parse failed')
      }
      
      const data = await response.json()
      console.log('Parse response:', data)
      
      // Check if this is a multiple items response
      if (data.type === 'multiple' && data.items && data.items.length > 0) {
        setMultipleItems(data.items)
        onFeedback(`✅ Found ${data.items.length} items! Review below.`)
        setLoading(false)
        return
      }
      
      // Single item - validate
      if (!data.item || data.item === 'item') {
        onFeedback('❌ Could not identify the item. Try "add 5 apples"')
        setLoading(false)
        return
      }
      
      if (!data.quantity || data.quantity <= 0) {
        onFeedback('❌ Could not identify quantity')
        setLoading(false)
        return
      }
      
      setPreview(data)
      onFeedback(`✅ Ready to ${data.action}: ${data.quantity} × ${data.item}`)
    } catch (error) {
      console.error('Parse error:', error)
      onFeedback(`❌ ${error.message}`)
    }
    setLoading(false)
  }

  const confirmAction = async () => {
    if (!preview) return
    
    const endpoint = preview.action === 'add' ? '/api/inventory/add' : '/api/inventory/remove'
    
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          name: preview.item.toLowerCase(), 
          quantity: preview.quantity 
        })
      })
      
      if (!response.ok) throw new Error('Operation failed')
      
      const data = await response.json()
      onFeedback(`🎉 ${data.message}`)
      setPreview(null)
      setInput('')
      onSuccess()
    } catch (error) {
      onFeedback(`❌ Failed to update inventory`)
    }
  }

  const confirmMultipleItems = async () => {
    if (!multipleItems) return
    
    const successCount = multipleItems.filter(item => item.success).length
    const failedItems = multipleItems.filter(item => !item.success).map(item => item.item)
    
    if (successCount === multipleItems.length) {
      onFeedback(`🎉 Added all ${multipleItems.length} items to inventory!`)
    } else {
      onFeedback(`⚠️ Added ${successCount}/${multipleItems.length} items. Failed: ${failedItems.join(', ')}`)
    }
    
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
    { text: 'add 5 apples', icon: '🍎', desc: 'Add 5 apples' },
    { text: 'add 10 biscuits', icon: '🍪', desc: 'Add 10 biscuits' },
    { text: 'remove 3 namkeen', icon: '🥨', desc: 'Remove 3 namkeen' },
    { text: '10 toothpaste, 10 water bottles, 15 notebooks', icon: '📦', desc: 'Add multiple items' },
    { text: 'add 5 apples and 3 bananas and 2 oranges', icon: '🍎🍌🍊', desc: 'Add multiple fruits' },
    { text: '10 biscuits, 5 namkeen, 3 chips', icon: '🍪', desc: 'Add multiple snacks' },
    { text: 'stock 20 pencils and 15 erasers', icon: '✏️', desc: 'Add stationery' }
  ]

  return (
    <div style={{ padding: '20px' }}>
      {/* Voice Button */}
      <div style={{ textAlign: 'center', marginBottom: '24px' }}>
        <button 
          onClick={isListening ? stopVoice : startVoice}
          style={{
            width: '120px',
            height: '120px',
            borderRadius: '50%',
            background: isListening ? '#ff4444' : 'linear-gradient(135deg, #4CAF50 0%, #45a049 100%)',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            margin: '0 auto',
            transition: 'all 0.3s ease',
            boxShadow: isListening ? '0 0 20px rgba(255,68,68,0.5)' : '0 4px 20px rgba(76,175,80,0.3)'
          }}
        >
          <div style={{ fontSize: '40px' }}>{isListening ? '🔴' : '🎤'}</div>
          <span style={{ fontSize: '12px', color: 'white', fontWeight: '500' }}>
            {isListening ? 'Listening...' : 'Click to Speak'}
          </span>
        </button>
        <p style={{ fontSize: '12px', color: '#666', marginTop: '8px' }}>
          Try: "10 toothpaste, 10 water bottles, 15 notebooks"
        </p>
      </div>

      {/* Input Area */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{
          display: 'flex',
          gap: '8px',
          background: '#f5f5f7',
          borderRadius: '16px',
          padding: '4px',
          border: '1px solid #e9ecef'
        }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder='Type: "10 toothpaste, 10 water bottles, 15 notebooks"'
            style={{
              flex: 1,
              padding: '14px 16px',
              fontSize: '14px',
              border: 'none',
              background: 'transparent',
              outline: 'none',
              fontFamily: 'inherit'
            }}
            onKeyPress={(e) => e.key === 'Enter' && parseCommand(input)}
          />
          <button 
            onClick={() => parseCommand(input)} 
            disabled={loading || !input.trim()}
            style={{
              padding: '12px 24px',
              fontSize: '14px',
              background: (loading || !input.trim()) ? '#ccc' : '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '12px',
              cursor: (loading || !input.trim()) ? 'not-allowed' : 'pointer',
              fontWeight: '600'
            }}
          >
            {loading ? '⟳' : 'Parse'}
          </button>
        </div>
      </div>

      {/* Example Commands */}
      <div style={{ marginBottom: '20px' }}>
        <p style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>💡 Try these commands:</p>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {exampleCommands.map((cmd, i) => (
            <button
              key={i}
              onClick={() => {
                setInput(cmd.text)
                parseCommand(cmd.text)
              }}
              style={{
                padding: '6px 12px',
                fontSize: '11px',
                background: '#f0f0f0',
                border: '1px solid #ddd',
                borderRadius: '20px',
                cursor: 'pointer',
                transition: 'all 0.2s',
                whiteSpace: 'nowrap'
              }}
              title={cmd.desc}
            >
              <span style={{ marginRight: '4px' }}>{cmd.icon}</span>
              {cmd.text.length > 35 ? cmd.text.substring(0, 35) + '...' : cmd.text}
            </button>
          ))}
        </div>
      </div>

      {/* Single Item Preview */}
      {preview && (
        <div style={{
          marginTop: '20px',
          padding: '20px',
          background: 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)',
          borderRadius: '16px'
        }}>
          <h3 style={{ margin: '0 0 10px 0' }}>📋 Single Item</h3>
          <p style={{ fontSize: '24px', margin: '10px 0', fontWeight: 'bold' }}>
            {preview.quantity} × {preview.item}
          </p>
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', marginTop: '15px' }}>
            <button onClick={confirmAction} style={{ background: '#4CAF50', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>✅ Confirm</button>
            <button onClick={cancelAction} style={{ background: '#f44336', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>❌ Cancel</button>
          </div>
        </div>
      )}

      {/* Multiple Items Preview */}
      {multipleItems && (
        <div style={{
          marginTop: '20px',
          padding: '20px',
          background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)',
          borderRadius: '16px'
        }}>
          <h3 style={{ margin: '0 0 10px 0' }}>📦 Multiple Items</h3>
          <div style={{ marginBottom: '15px' }}>
            {multipleItems.map((item, idx) => (
              <div key={idx} style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '8px 0',
                borderBottom: '1px solid rgba(0,0,0,0.1)'
              }}>
                <span style={{ textTransform: 'capitalize' }}>{item.item}</span>
                <span><strong>{item.quantity}</strong> units</span>
                <span style={{ color: item.success ? '#4CAF50' : '#f44336' }}>
                  {item.success ? '✓' : '✗'}
                </span>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
            <button onClick={confirmMultipleItems} style={{ background: '#4CAF50', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>✅ Add All</button>
            <button onClick={cancelMultipleItems} style={{ background: '#f44336', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>❌ Cancel</button>
          </div>
        </div>
      )}
    </div>
  )
}