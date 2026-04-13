import { useRef, useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function CameraDetector({ onFeedback, onSuccess }) {
  const videoRef = useRef(null)
  const fileInputRef = useRef(null)
  const [cameraActive, setCameraActive] = useState(false)
  const [detectedItem, setDetectedItem] = useState(null)
  const [quantity, setQuantity] = useState('')
  const [showQuantityInput, setShowQuantityInput] = useState(false)
  const [isDetecting, setIsDetecting] = useState(false)
  const [confidence, setConfidence] = useState(0)
  const [activeMode, setActiveMode] = useState('camera')
  const [uploadedImage, setUploadedImage] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [uploadedVideo, setUploadedVideo] = useState(null)
  const [videoPreview, setVideoPreview] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [detectedObjects, setDetectedObjects] = useState([])
  const streamRef = useRef(null)

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  // Camera functions
  const startCamera = async () => {
    onFeedback('📸 Requesting camera access...')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.onloadedmetadata = () => {
          videoRef.current.play()
          setCameraActive(true)
          onFeedback('✅ Camera ready!')
        }
      }
    } catch (error) {
      onFeedback('❌ Camera access denied')
    }
  }

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    if (videoRef.current) videoRef.current.srcObject = null
    setCameraActive(false)
    onFeedback('📸 Camera stopped')
  }

  const captureAndDetect = async () => {
    if (!videoRef.current) {
      onFeedback('❌ Camera not ready')
      return
    }
    
    setIsDetecting(true)
    onFeedback('📸 Capturing...')
    
    try {
      const canvas = document.createElement('canvas')
      canvas.width = videoRef.current.videoWidth
      canvas.height = videoRef.current.videoHeight
      canvas.getContext('2d').drawImage(videoRef.current, 0, 0)
      
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg'))
      const formData = new FormData()
      formData.append('image', blob)
      
      const response = await fetch(`${API_BASE}/api/vision/detect`, { 
        method: 'POST', 
        body: formData 
      })
      
      const data = await response.json()
      
      if (data.success && data.detected_item) {
        setDetectedItem(data.detected_item)
        setConfidence(data.confidence)
        setShowQuantityInput(true)
        onFeedback(`✅ Detected: ${data.detected_item} (${Math.round(data.confidence * 100)}% confidence)`)
      } else {
        onFeedback('❌ No object detected. Try again.')
      }
    } catch (error) {
      onFeedback('❌ Detection failed')
    }
    setIsDetecting(false)
  }

  // Image Upload functions
  const handleImageUpload = (event) => {
    const file = event.target.files[0]
    if (file) {
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result)
        setUploadedImage(file)
        onFeedback(`📁 Image loaded: ${file.name}`)
      }
      reader.readAsDataURL(file)
    }
  }

  const processUploadedImage = async () => {
    if (!uploadedImage) {
      onFeedback('❌ Please select an image first')
      return
    }
    
    setIsProcessing(true)
    onFeedback('🔍 Analyzing image...')
    
    try {
      const formData = new FormData()
      formData.append('image', uploadedImage)
      
      const response = await fetch(`${API_BASE}/api/vision/detect`, { 
        method: 'POST', 
        body: formData 
      })
      
      const data = await response.json()
      
      if (data.success && data.detected_item) {
        setDetectedItem(data.detected_item)
        setConfidence(data.confidence)
        setShowQuantityInput(true)
        onFeedback(`✅ Detected: ${data.detected_item} (${Math.round(data.confidence * 100)}% confidence)`)
      } else {
        onFeedback('❌ No object detected in image')
      }
    } catch (error) {
      onFeedback('❌ Detection failed')
    }
    setIsProcessing(false)
  }

  // Video Upload functions
  const handleVideoUpload = (event) => {
    const file = event.target.files[0]
    if (file) {
      const reader = new FileReader()
      reader.onloadend = () => {
        setVideoPreview(reader.result)
        setUploadedVideo(file)
        onFeedback(`📹 Video loaded: ${file.name}`)
      }
      reader.readAsDataURL(file)
    }
  }

  const processVideo = async () => {
    if (!uploadedVideo) {
      onFeedback('❌ Please select a video first')
      return
    }
    
    setIsProcessing(true)
    onFeedback('🔍 Analyzing video for objects...')
    
    try {
      const formData = new FormData()
      formData.append('video', uploadedVideo)
      
      const response = await fetch(`${API_BASE}/api/vision/detect-video`, { 
        method: 'POST', 
        body: formData 
      })
      
      const data = await response.json()
      
      if (data.success && data.detections && data.detections.length > 0) {
        setDetectedObjects(data.detections)
        onFeedback(`✅ Found ${data.detections.length} objects in video!`)
      } else {
        onFeedback('❌ No objects detected in video')
      }
    } catch (error) {
      onFeedback('❌ Video detection failed')
    }
    setIsProcessing(false)
  }

  const resetUpload = () => {
    setUploadedImage(null)
    setImagePreview(null)
    setUploadedVideo(null)
    setVideoPreview(null)
    setDetectedObjects([])
    onFeedback('Upload cleared')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const addToInventory = async () => {
    const qty = parseInt(quantity)
    if (!qty || qty <= 0) {
      onFeedback('❌ Enter valid quantity')
      return
    }
    
    try {
      const response = await fetch(`${API_BASE}/api/inventory/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: detectedItem.toLowerCase(), quantity: qty })
      })
      
      if (!response.ok) throw new Error('Failed')
      
      onFeedback(`✅ Added ${qty} × ${detectedItem}`)
      setShowQuantityInput(false)
      setDetectedItem(null)
      setQuantity('')
      onSuccess()
      resetUpload()
      if (cameraActive) stopCamera()
    } catch (error) {
      onFeedback('❌ Failed to add')
    }
  }

  const addDetectedObject = async (item) => {
    const qty = prompt(`How many ${item.item} to add?`, "1")
    if (!qty) return
    
    const quantity = parseInt(qty)
    if (isNaN(quantity) || quantity <= 0) return
    
    try {
      const response = await fetch(`${API_BASE}/api/inventory/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: item.item.toLowerCase(), quantity })
      })
      
      if (response.ok) {
        onFeedback(`✅ Added ${quantity} × ${item.item}`)
        onSuccess()
      }
    } catch (error) {
      onFeedback('❌ Failed to add')
    }
  }

  return (
    <div style={styles.container}>
      {/* Mode Toggle */}
      <div style={styles.modeToggle}>
        <button 
          className={activeMode === 'camera' ? 'active' : ''} 
          onClick={() => setActiveMode('camera')}
          style={styles.modeButton(activeMode === 'camera')}
        >
          📸 Camera
        </button>
        <button 
          className={activeMode === 'image' ? 'active' : ''} 
          onClick={() => setActiveMode('image')}
          style={styles.modeButton(activeMode === 'image')}
        >
          🖼️ Image
        </button>
        <button 
          className={activeMode === 'video' ? 'active' : ''} 
          onClick={() => setActiveMode('video')}
          style={styles.modeButton(activeMode === 'video')}
        >
          🎥 Video
        </button>
      </div>

      {/* Camera Mode */}
      {activeMode === 'camera' && (
        <>
          {!cameraActive ? (
            <div style={styles.placeholder}>
              <div style={styles.placeholderIcon}>📸</div>
              <h3 style={styles.placeholderTitle}>Scan Items with Camera</h3>
              <p style={styles.placeholderText}>Point your camera at any object to detect and add to inventory</p>
              <button onClick={startCamera} style={styles.startButton}>Start Camera</button>
            </div>
          ) : (
            <div>
              <div style={styles.videoWrapper}>
                <video ref={videoRef} autoPlay playsInline style={styles.videoPreview} />
                <div style={styles.scanFrame}></div>
                <div style={styles.scanHint}>Center object in frame</div>
              </div>
              <div style={styles.buttonGroup}>
                <button onClick={captureAndDetect} disabled={isDetecting} style={styles.captureButton(isDetecting)}>
                  {isDetecting ? '⟳ Detecting...' : '📸 Capture & Detect'}
                </button>
                <button onClick={stopCamera} style={styles.stopButton}>🛑 Stop Camera</button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Image Upload Mode */}
      {activeMode === 'image' && (
        <div>
          {!imagePreview ? (
            <div style={styles.placeholder}>
              <div style={styles.placeholderIcon}>🖼️</div>
              <h3 style={styles.placeholderTitle}>Upload an Image</h3>
              <p style={styles.placeholderText}>Select an image from your device to detect objects</p>
              <input type="file" accept="image/*" onChange={handleImageUpload} style={{ display: 'none' }} id="image-upload" ref={fileInputRef} />
              <label htmlFor="image-upload" style={styles.uploadButton}>Choose Image</label>
            </div>
          ) : (
            <div>
              <img src={imagePreview} alt="Preview" style={styles.previewImage} />
              <div style={styles.buttonGroup}>
                <button onClick={processUploadedImage} disabled={isProcessing} style={styles.detectButton(isProcessing)}>
                  {isProcessing ? '⟳ Processing...' : '🔍 Detect Object'}
                </button>
                <button onClick={resetUpload} style={styles.resetButton}>✕ Change Image</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Video Upload Mode */}
      {activeMode === 'video' && (
        <div>
          {!videoPreview ? (
            <div style={styles.placeholder}>
              <div style={styles.placeholderIcon}>🎥</div>
              <h3 style={styles.placeholderTitle}>Upload a Video</h3>
              <p style={styles.placeholderText}>Upload a video file to detect objects frame by frame</p>
              <input type="file" accept="video/*" onChange={handleVideoUpload} style={{ display: 'none' }} id="video-upload" />
              <label htmlFor="video-upload" style={styles.uploadButton}>Choose Video</label>
            </div>
          ) : (
            <div>
              <video src={videoPreview} controls style={styles.previewVideo} />
              <div style={styles.buttonGroup}>
                <button onClick={processVideo} disabled={isProcessing} style={styles.detectButton(isProcessing)}>
                  {isProcessing ? '⟳ Processing...' : '🔍 Detect Objects'}
                </button>
                <button onClick={resetUpload} style={styles.resetButton}>✕ Change Video</button>
              </div>
              {detectedObjects.length > 0 && (
                <div style={styles.detectedList}>
                  <h4 style={styles.detectedTitle}>📋 Detected Objects:</h4>
                  {detectedObjects.map((obj, idx) => (
                    <div key={idx} style={styles.detectedItem}>
                      <span>{obj.item} ({Math.round(obj.confidence * 100)}%)</span>
                      <button onClick={() => addDetectedObject(obj)} style={styles.addDetectedBtn}>➕ Add</button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Add Quantity Modal */}
      {showQuantityInput && (
        <div style={styles.modal}>
          <div style={styles.modalContent}>
            <h3 style={styles.modalTitle}>Add to Inventory</h3>
            <div style={styles.detectedInfo}>
              <span>Detected:</span>
              <strong>{detectedItem}</strong>
              <span style={styles.confidenceBadge}>{Math.round(confidence * 100)}%</span>
            </div>
            <input 
              type="number" 
              value={quantity} 
              onChange={(e) => setQuantity(e.target.value)} 
              placeholder="Enter quantity" 
              style={styles.modalInput}
              autoFocus 
            />
            <div style={styles.modalActions}>
              <button onClick={() => setShowQuantityInput(false)} style={styles.modalCancel}>Cancel</button>
              <button onClick={addToInventory} style={styles.modalConfirm}>Add to Stock</button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse {
          0% { transform: scale(1); }
          50% { transform: scale(1.02); }
          100% { transform: scale(1); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

const styles = {
  container: {
    padding: '24px',
    background: 'linear-gradient(135deg, #ffffff 0%, #fff8f0 100%)',
    borderRadius: '28px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.06)',
    border: '1px solid rgba(255, 152, 0, 0.15)',
    animation: 'fadeIn 0.3s ease'
  },
  modeToggle: {
    display: 'flex',
    gap: '12px',
    marginBottom: '24px',
    background: 'rgba(255, 255, 255, 0.9)',
    borderRadius: '60px',
    padding: '6px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.03)'
  },
  modeButton: (isActive) => ({
    flex: 1,
    padding: '12px 20px',
    borderRadius: '50px',
    border: 'none',
    background: isActive ? 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)' : 'transparent',
    color: isActive ? 'white' : '#666',
    cursor: 'pointer',
    fontWeight: '600',
    fontSize: '14px',
    transition: 'all 0.3s ease',
    boxShadow: isActive ? '0 4px 12px rgba(255, 152, 0, 0.3)' : 'none'
  }),
  placeholder: {
    textAlign: 'center',
    padding: '48px 24px',
    background: 'linear-gradient(135deg, #fff8f0 0%, #fff0e0 100%)',
    borderRadius: '24px',
    border: '2px dashed #FF9800'
  },
  placeholderIcon: {
    fontSize: '64px',
    marginBottom: '16px'
  },
  placeholderTitle: {
    fontSize: '1.2rem',
    fontWeight: '600',
    color: '#FF9800',
    marginBottom: '8px'
  },
  placeholderText: {
    fontSize: '13px',
    color: '#8a8a8e',
    marginBottom: '24px'
  },
  startButton: {
    padding: '12px 28px',
    background: 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '40px',
    cursor: 'pointer',
    fontWeight: '600',
    fontSize: '14px',
    transition: 'all 0.3s ease',
    boxShadow: '0 4px 12px rgba(255, 152, 0, 0.3)'
  },
  uploadButton: {
    padding: '12px 28px',
    background: 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '40px',
    cursor: 'pointer',
    fontWeight: '600',
    fontSize: '14px',
    display: 'inline-block',
    transition: 'all 0.3s ease'
  },
  videoWrapper: {
    position: 'relative',
    borderRadius: '20px',
    overflow: 'hidden',
    border: '2px solid #FF9800',
    backgroundColor: '#000',
    marginBottom: '16px'
  },
  videoPreview: {
    width: '100%',
    height: 'auto',
    display: 'block'
  },
  scanFrame: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: '70%',
    height: '60%',
    border: '2px solid rgba(255, 152, 0, 0.8)',
    borderRadius: '16px',
    pointerEvents: 'none',
    animation: 'pulse 2s infinite'
  },
  scanHint: {
    position: 'absolute',
    bottom: '16px',
    left: '50%',
    transform: 'translateX(-50%)',
    background: 'rgba(0, 0, 0, 0.7)',
    color: 'white',
    padding: '6px 16px',
    borderRadius: '30px',
    fontSize: '12px',
    pointerEvents: 'none'
  },
  buttonGroup: {
    display: 'flex',
    gap: '12px',
    marginTop: '16px'
  },
  captureButton: (disabled) => ({
    flex: 1,
    padding: '14px',
    background: disabled ? '#ccc' : 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '40px',
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontWeight: '600',
    fontSize: '14px',
    transition: 'all 0.3s ease'
  }),
  stopButton: {
    padding: '14px 24px',
    background: 'linear-gradient(135deg, #f44336 0%, #d32f2f 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '40px',
    cursor: 'pointer',
    fontWeight: '600',
    fontSize: '14px',
    transition: 'all 0.3s ease'
  },
  detectButton: (disabled) => ({
    flex: 1,
    padding: '14px',
    background: disabled ? '#ccc' : 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '40px',
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontWeight: '600',
    fontSize: '14px'
  }),
  resetButton: {
    padding: '14px 24px',
    background: 'linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '40px',
    cursor: 'pointer',
    fontWeight: '600',
    fontSize: '14px'
  },
  previewImage: {
    width: '100%',
    maxWidth: '500px',
    borderRadius: '20px',
    border: '2px solid #FF9800',
    marginBottom: '16px'
  },
  previewVideo: {
    width: '100%',
    maxWidth: '500px',
    borderRadius: '20px',
    border: '2px solid #FF9800',
    marginBottom: '16px'
  },
  detectedList: {
    marginTop: '20px',
    padding: '16px',
    background: 'white',
    borderRadius: '20px',
    border: '1px solid rgba(255, 152, 0, 0.2)'
  },
  detectedTitle: {
    margin: '0 0 12px 0',
    fontSize: '14px',
    fontWeight: '600',
    color: '#FF9800'
  },
  detectedItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 12px',
    borderBottom: '1px solid #f0f0f0'
  },
  addDetectedBtn: {
    padding: '4px 12px',
    background: '#4CAF50',
    color: 'white',
    border: 'none',
    borderRadius: '20px',
    cursor: 'pointer',
    fontSize: '12px'
  },
  modal: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    backdropFilter: 'blur(4px)'
  },
  modalContent: {
    background: 'white',
    padding: '28px',
    borderRadius: '28px',
    width: '340px',
    maxWidth: '90%',
    textAlign: 'center',
    borderTop: '4px solid #FF9800',
    animation: 'fadeIn 0.3s ease'
  },
  modalTitle: {
    margin: '0 0 16px 0',
    fontSize: '1.2rem',
    fontWeight: '600',
    color: '#333'
  },
  detectedInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px',
    background: 'rgba(255, 152, 0, 0.1)',
    borderRadius: '16px',
    marginBottom: '16px'
  },
  confidenceBadge: {
    marginLeft: 'auto',
    fontSize: '11px',
    background: '#FF9800',
    padding: '2px 10px',
    borderRadius: '20px',
    color: 'white'
  },
  modalInput: {
    width: '100%',
    padding: '14px',
    fontSize: '16px',
    border: '1px solid #e0e0e0',
    borderRadius: '14px',
    marginBottom: '20px',
    boxSizing: 'border-box'
  },
  modalActions: {
    display: 'flex',
    gap: '12px'
  },
  modalCancel: {
    flex: 1,
    padding: '12px',
    background: '#f0f0f0',
    border: 'none',
    borderRadius: '40px',
    cursor: 'pointer',
    fontWeight: '500',
    transition: 'all 0.2s'
  },
  modalConfirm: {
    flex: 1,
    padding: '12px',
    background: 'linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '40px',
    cursor: 'pointer',
    fontWeight: '600',
    transition: 'all 0.2s',
    boxShadow: '0 2px 8px rgba(76, 175, 80, 0.3)'
  }
}