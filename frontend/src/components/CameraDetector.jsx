import { useRef, useState, useEffect } from 'react'
const API_BASE = 'http://localhost:8000'
export default function CameraDetector({ onFeedback, onSuccess }) {
  const videoRef = useRef(null)
  const fileInputRef = useRef(null)
  const [activeMode, setActiveMode] = useState('upload') // 'camera' or 'upload'
  const [cameraActive, setCameraActive] = useState(false)
  const [detectedItem, setDetectedItem] = useState(null)
  const [quantity, setQuantity] = useState('')
  const [showQuantityInput, setShowQuantityInput] = useState(false)
  const [confidence, setConfidence] = useState(0)
  const [debugInfo, setDebugInfo] = useState('Ready')
  const [uploadedVideo, setUploadedVideo] = useState(null)
  const [videoPreview, setVideoPreview] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [detections, setDetections] = useState([])
  const streamRef = useRef(null)

  // Cleanup
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  // ==================== CAMERA MODE (Optional) ====================
  
  const startCamera = async () => {
    setDebugInfo('Requesting camera...')
    onFeedback('📸 Requesting camera...')
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: { ideal: 640 }, height: { ideal: 480 } } 
      })
      streamRef.current = stream
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.onloadedmetadata = () => {
          videoRef.current.play()
          setCameraActive(true)
          setDebugInfo('Camera ready!')
          onFeedback('✅ Camera ready!')
        }
      }
    } catch (error) {
      setDebugInfo(`Error: ${error.message}`)
      onFeedback('❌ Camera access denied')
    }
  }

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setCameraActive(false)
    setDebugInfo('Camera stopped')
    onFeedback('📸 Camera stopped')
  }

  const captureFromCamera = async () => {
    if (!videoRef.current || !videoRef.current.videoWidth) {
      onFeedback('❌ Camera not ready')
      return
    }
    
    setIsProcessing(true)
    onFeedback('📸 Capturing...')
    
    try {
      const canvas = document.createElement('canvas')
      canvas.width = videoRef.current.videoWidth
      canvas.height = videoRef.current.videoHeight
      canvas.getContext('2d').drawImage(videoRef.current, 0, 0)
      
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8))
      const formData = new FormData()
      formData.append('image', blob)
      
      const response = await fetch(`${API_BASE}/api/vision/detect`, { 
        method: 'POST', 
        body: formData 
      })
      
      const data = await response.json()
      
      if (data.success && data.detected_item && data.detected_item !== 'unknown') {
        setDetectedItem(data.detected_item)
        setConfidence(data.confidence)
        setShowQuantityInput(true)
        onFeedback(`✅ Detected: ${data.detected_item}`)
      } else {
        onFeedback('❌ No object detected')
      }
    } catch (error) {
      onFeedback('❌ Detection failed')
    }
    setIsProcessing(false)
  }

  // ==================== VIDEO UPLOAD MODE ====================
  
  const handleVideoUpload = (event) => {
    const file = event.target.files[0]
    if (file) {
      // Check if it's a video file
      if (!file.type.startsWith('video/')) {
        onFeedback('❌ Please upload a video file (MP4, AVI, MOV)')
        return
      }
      
      const reader = new FileReader()
      reader.onloadend = () => {
        setVideoPreview(reader.result)
        setUploadedVideo(file)
        setDebugInfo(`Video loaded: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`)
        onFeedback(`📹 Video loaded: ${file.name}`)
        setDetections([])
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
    setDebugInfo('Processing video...')
    onFeedback('🔍 Analyzing video for objects...')
    
    try {
      const formData = new FormData()
      formData.append('video', uploadedVideo)
      
      const response = await fetch(`${API_BASE}/api/vision/detect-video`, { 
        method: 'POST', 
        body: formData 
      })
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }
      
      const data = await response.json()
      console.log('Video detection results:', data)
      
      if (data.success && data.detections && data.detections.length > 0) {
        setDetections(data.detections)
        setDebugInfo(`Detected ${data.detections.length} objects in video`)
        onFeedback(`✅ Found ${data.detections.length} objects in video! Click to add.`)
      } else {
        setDebugInfo('No objects detected in video')
        onFeedback('❌ No objects detected in video. Try a clearer video.')
      }
    } catch (error) {
      console.error('Processing error:', error)
      setDebugInfo(`Error: ${error.message}`)
      onFeedback(`❌ Processing failed: ${error.message}`)
    }
    setIsProcessing(false)
  }

  const resetUpload = () => {
    setUploadedVideo(null)
    setVideoPreview(null)
    setDetections([])
    setDebugInfo('Upload reset')
    onFeedback('📹 Upload cleared')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // ==================== ADD TO INVENTORY ====================
  
  const addToInventory = async (item, conf) => {
    const qty = prompt(`How many ${item} to add?`, "1")
    if (!qty) return
    
    const quantityNum = parseInt(qty)
    if (isNaN(quantityNum) || quantityNum <= 0) {
      onFeedback('❌ Please enter a valid quantity')
      return
    }
    
    try {
      const response = await fetch(`${API_BASE}/api/inventory/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: item.toLowerCase(), quantity: quantityNum })
      })
      
      if (!response.ok) throw new Error('Failed to add')
      
      onFeedback(`✅ Added ${quantityNum} × ${item} to inventory`)
      onSuccess()
    } catch (error) {
      onFeedback('❌ Failed to add to inventory')
    }
  }

  // ==================== RENDER ====================
  
  return (
    <div style={{ padding: '20px' }}>
      {/* Mode Toggle */}
      <div style={{
        display: 'flex',
        gap: '10px',
        marginBottom: '20px',
        background: '#f0f0f0',
        borderRadius: '50px',
        padding: '4px'
      }}>
        <button
          onClick={() => setActiveMode('upload')}
          style={{
            flex: 1,
            padding: '10px',
            borderRadius: '40px',
            border: 'none',
            background: activeMode === 'upload' ? '#FF9800' : 'transparent',
            color: activeMode === 'upload' ? 'white' : '#666',
            cursor: 'pointer',
            fontWeight: '500'
          }}
        >
          📹 Upload Video
        </button>
        <button
          onClick={() => setActiveMode('camera')}
          style={{
            flex: 1,
            padding: '10px',
            borderRadius: '40px',
            border: 'none',
            background: activeMode === 'camera' ? '#FF9800' : 'transparent',
            color: activeMode === 'camera' ? 'white' : '#666',
            cursor: 'pointer',
            fontWeight: '500'
          }}
        >
          📸 Live Camera
        </button>
      </div>

      {/* Debug Info */}
      <div style={{
        background: '#e8f5e9',
        padding: '8px 12px',
        borderRadius: '8px',
        marginBottom: '15px',
        fontSize: '12px',
        fontFamily: 'monospace',
        textAlign: 'center',
        border: '1px solid #4CAF50'
      }}>
        🔍 YOLO: {debugInfo}
      </div>

      {/* Video Upload Mode */}
      {activeMode === 'upload' && (
        <div>
          {!videoPreview ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', background: 'rgba(255,255,255,0.9)', borderRadius: '20px', border: '2px dashed #FF9800' }}>
              <div style={{ fontSize: '64px', marginBottom: '16px' }}>📹</div>
              <h3 style={{ marginBottom: '8px', color: '#FF9800' }}>Upload Video for Object Detection</h3>
              <p style={{ color: '#666', marginBottom: '24px' }}>
                Upload MP4, AVI, or MOV file - YOLO will detect objects frame by frame
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                onChange={handleVideoUpload}
                style={{ display: 'none' }}
                id="video-upload"
              />
              <label 
                htmlFor="video-upload" 
                style={{
                  padding: '14px 28px',
                  background: 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '30px',
                  fontSize: '16px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  display: 'inline-block'
                }}
              >
                Choose Video File
              </label>
            </div>
          ) : (
            <div>
              <div style={{ 
                borderRadius: '20px', 
                overflow: 'hidden', 
                border: '2px solid #FF9800',
                backgroundColor: '#f5f5f5',
                textAlign: 'center'
              }}>
                <video 
                  src={videoPreview} 
                  controls 
                  style={{ width: '100%', maxHeight: '400px' }} 
                />
              </div>
              
              <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                <button 
                  onClick={processVideo} 
                  disabled={isProcessing}
                  style={{
                    flex: 1,
                    padding: '14px',
                    background: isProcessing ? '#ccc' : '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '30px',
                    fontSize: '16px',
                    fontWeight: '600',
                    cursor: isProcessing ? 'not-allowed' : 'pointer'
                  }}
                >
                  {isProcessing ? '⟳ Processing...' : '🔍 Detect Objects'}
                </button>
                <button 
                  onClick={resetUpload} 
                  style={{
                    padding: '14px 24px',
                    background: '#f44336',
                    color: 'white',
                    border: 'none',
                    borderRadius: '30px',
                    fontSize: '14px',
                    cursor: 'pointer'
                  }}
                >
                  ✕ Change Video
                </button>
              </div>
            </div>
          )}
          
          {/* Detected Objects List */}
          {detections.length > 0 && (
            <div style={{
              marginTop: '20px',
              padding: '16px',
              background: 'white',
              borderRadius: '16px',
              border: '1px solid #e0e0e0'
            }}>
              <h4 style={{ marginBottom: '12px' }}>🎯 Detected Objects</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {detections.map((det, idx) => (
                  <div key={idx} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px',
                    background: '#f9f9f9',
                    borderRadius: '10px'
                  }}>
                    <div>
                      <strong style={{ textTransform: 'capitalize' }}>{det.item}</strong>
                      <span style={{ marginLeft: '8px', fontSize: '12px', color: '#666' }}>
                        confidence: {Math.round(det.confidence * 100)}%
                      </span>
                    </div>
                    <button
                      onClick={() => addToInventory(det.item, det.confidence)}
                      style={{
                        padding: '6px 16px',
                        background: '#4CAF50',
                        color: 'white',
                        border: 'none',
                        borderRadius: '20px',
                        cursor: 'pointer'
                      }}
                    >
                      ➕ Add
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Camera Mode (Optional) */}
      {activeMode === 'camera' && (
        <div>
          {!cameraActive ? (
            <div style={{ textAlign: 'center', padding: '40px', background: '#f5f5f5', borderRadius: '20px' }}>
              <div style={{ fontSize: '64px' }}>📸</div>
              <h3>Live Camera Detection</h3>
              <button 
                onClick={startCamera} 
                style={{
                  padding: '12px 24px',
                  background: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '30px',
                  cursor: 'pointer',
                  marginTop: '16px'
                }}
              >
                Start Camera
              </button>
            </div>
          ) : (
            <div>
              <video ref={videoRef} autoPlay playsInline style={{ width: '100%', borderRadius: '10px', border: '2px solid #FF9800' }} />
              <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                <button onClick={captureFromCamera} disabled={isProcessing} style={{ flex: 1, padding: '12px', background: '#FF9800', color: 'white', border: 'none', borderRadius: '30px', cursor: 'pointer' }}>
                  {isProcessing ? 'Processing...' : 'Capture & Detect'}
                </button>
                <button onClick={stopCamera} style={{ padding: '12px 20px', background: '#f44336', color: 'white', border: 'none', borderRadius: '30px', cursor: 'pointer' }}>
                  Stop Camera
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}