import { useEffect, useState } from 'react'

export default function FeedbackMessage({ message }) {
  const [visible, setVisible] = useState(false)
  const [currentMessage, setCurrentMessage] = useState('')
  const [messageType, setMessageType] = useState('info')

  useEffect(() => {
    if (message) {
      setCurrentMessage(message)
      setVisible(true)
      
      // Determine message type based on content
      if (message.includes('✅') || message.includes('Added') || message.includes('added') || message.includes('Restocked')) {
        setMessageType('success')
      } else if (message.includes('❌') || message.includes('Error') || message.includes('Failed') || message.includes('failed')) {
        setMessageType('error')
      } else if (message.includes('🎤') || message.includes('Listening') || message.includes('Speak')) {
        setMessageType('voice')
      } else if (message.includes('📸') || message.includes('Camera') || message.includes('Detected')) {
        setMessageType('camera')
      } else if (message.includes('🔍') || message.includes('Search') || message.includes('Filters')) {
        setMessageType('info')
      } else {
        setMessageType('info')
      }
      
      const timer = setTimeout(() => setVisible(false), 3500)
      return () => clearTimeout(timer)
    }
  }, [message])

  // Get dynamic styles based on message type
  const getStyles = () => {
    switch(messageType) {
      case 'success':
        return {
          background: 'linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)',
          icon: '✅',
          boxShadow: '0 4px 15px rgba(76, 175, 80, 0.3)'
        }
      case 'error':
        return {
          background: 'linear-gradient(135deg, #f44336 0%, #d32f2f 100%)',
          icon: '❌',
          boxShadow: '0 4px 15px rgba(244, 67, 54, 0.3)'
        }
      case 'voice':
        return {
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          icon: '🎤',
          boxShadow: '0 4px 15px rgba(102, 126, 234, 0.3)'
        }
      case 'camera':
        return {
          background: 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)',
          icon: '📸',
          boxShadow: '0 4px 15px rgba(255, 152, 0, 0.3)'
        }
      default:
        return {
          background: 'linear-gradient(135deg, #2196F3 0%, #1976D2 100%)',
          icon: 'ℹ️',
          boxShadow: '0 4px 15px rgba(33, 150, 243, 0.3)'
        }
    }
  }

  const styles = getStyles()

  if (!visible || !currentMessage) return null

  // Extract icon from message if present, otherwise use type icon
  const hasIcon = currentMessage.match(/[✅❌🎤📸🔍⚠️💡]/)
  const displayIcon = hasIcon ? hasIcon[0] : styles.icon

  return (
    <div style={{
      position: 'fixed',
      bottom: '24px',
      right: '24px',
      background: styles.background,
      color: 'white',
      padding: '14px 24px',
      borderRadius: '16px',
      boxShadow: styles.boxShadow,
      zIndex: 1000,
      animation: 'slideInRight 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
      backdropFilter: 'blur(10px)',
      maxWidth: '380px',
      minWidth: '280px',
      fontFamily: 'inherit',
      border: '1px solid rgba(255, 255, 255, 0.2)'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px'
      }}>
        <div style={{
          fontSize: '22px',
          background: 'rgba(255, 255, 255, 0.2)',
          width: '36px',
          height: '36px',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          {displayIcon}
        </div>
        <div style={{
          flex: 1,
          fontSize: '14px',
          fontWeight: '500',
          lineHeight: '1.4',
          wordBreak: 'break-word'
        }}>
          {currentMessage}
        </div>
        <button
          onClick={() => setVisible(false)}
          style={{
            background: 'rgba(255, 255, 255, 0.2)',
            border: 'none',
            color: 'white',
            width: '24px',
            height: '24px',
            borderRadius: '50%',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '14px',
            transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => e.target.style.background = 'rgba(255, 255, 255, 0.3)'}
          onMouseLeave={(e) => e.target.style.background = 'rgba(255, 255, 255, 0.2)'}
        >
          ✕
        </button>
      </div>
      
      {/* Progress bar animation */}
      <div style={{
        position: 'absolute',
        bottom: '0',
        left: '0',
        height: '3px',
        background: 'rgba(255, 255, 255, 0.5)',
        width: '100%',
        borderRadius: '0 0 16px 16px',
        overflow: 'hidden'
      }}>
        <div style={{
          height: '100%',
          width: '100%',
          background: 'rgba(255, 255, 255, 0.8)',
          animation: 'shrink 3.5s linear forwards',
          transformOrigin: 'left'
        }} />
      </div>
      
      <style>{`
        @keyframes slideInRight {
          from {
            opacity: 0;
            transform: translateX(100px) scale(0.8);
          }
          to {
            opacity: 1;
            transform: translateX(0) scale(1);
          }
        }
        
        @keyframes shrink {
          from {
            transform: scaleX(1);
          }
          to {
            transform: scaleX(0);
          }
        }
        
        @keyframes pulse {
          0% { transform: scale(1); }
          50% { transform: scale(1.05); }
          100% { transform: scale(1); }
        }
      `}</style>
    </div>
  )
}