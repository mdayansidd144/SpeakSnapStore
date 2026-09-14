import {
  useEffect,
  useRef,
  useState
} from 'react'

const API_BASE =
  import.meta.env.VITE_API_URL || 'http://localhost:8000'

function CameraDetector({
  onFeedback,
  onSuccess
}) {
  const [activeMode, setActiveMode] =
    useState('camera')

  const [cameraActive, setCameraActive] =
    useState(false)

  const [stream, setStream] =
    useState(null)

  const [selectedFile, setSelectedFile] =
    useState(null)

  const [previewUrl, setPreviewUrl] =
    useState(null)

  const [detecting, setDetecting] =
    useState(false)

  const [results, setResults] =
    useState([])

  const [showQuantityModal, setShowQuantityModal] =
    useState(false)

  const [selectedItem, setSelectedItem] =
    useState(null)

  const [quantity, setQuantity] =
    useState(1)

  const videoRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach(
          (track) => track.stop()
        )
      }

      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [stream, previewUrl])

  const handleModeChange = (mode) => {
    stopCamera()

    setSelectedFile(null)
    setPreviewUrl(null)
    setResults([])

    setActiveMode(mode)
  }

  const startCamera = async () => {
    try {
      const mediaStream =
        await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: 'environment'
          },
          audio: false
        })

      setStream(mediaStream)
      setCameraActive(true)

      if (videoRef.current) {
        videoRef.current.srcObject =
          mediaStream
      }

      onFeedback?.(
        'Camera started'
      )
    } catch (error) {
      console.error(
        'Camera error:',
        error
      )

      onFeedback?.(
        'Unable to access the camera. Please check browser permissions.'
      )
    }
  }

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(
        (track) => track.stop()
      )
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null
    }

    setStream(null)
    setCameraActive(false)
  }

  const captureFrame = async () => {
    if (!videoRef.current) {
      return
    }

    const video =
      videoRef.current

    const canvas =
      document.createElement('canvas')

    canvas.width =
      video.videoWidth || 1280

    canvas.height =
      video.videoHeight || 720

    const context =
      canvas.getContext('2d')

    if (!context) {
      return
    }

    context.drawImage(
      video,
      0,
      0,
      canvas.width,
      canvas.height
    )

    canvas.toBlob(
      async (blob) => {
        if (!blob) {
          return
        }

        const file = new File(
          [blob],
          'camera-capture.jpg',
          {
            type: 'image/jpeg'
          }
        )

        await detectImage(file)
      },
      'image/jpeg',
      0.9
    )
  }

  const handleFileChange = (
    event
  ) => {
    const file =
      event.target.files?.[0]

    if (!file) {
      return
    }

    setSelectedFile(file)
    setResults([])

    if (previewUrl) {
      URL.revokeObjectURL(
        previewUrl
      )
    }

    setPreviewUrl(
      URL.createObjectURL(file)
    )
  }

  const detectImage = async (
    file
  ) => {
    try {
      setDetecting(true)
      setResults([])

      const formData =
        new FormData()

      formData.append(
        'file',
        file
      )

      const response =
        await fetch(
          `${API_BASE}/api/vision/detect`,
          {
            method: 'POST',
            body: formData
          }
        )

      if (!response.ok) {
        const errorText =
          await response.text()

        throw new Error(
          errorText ||
            `HTTP ${response.status}`
        )
      }

      const data =
        await response.json()

      const detections =
        Array.isArray(
          data?.detections
        )
          ? data.detections
          : Array.isArray(data)
            ? data
            : []

      setResults(
        detections
      )

      if (detections.length === 0) {
        onFeedback?.(
          'No recognizable inventory item was detected'
        )
      } else {
        onFeedback?.(
          `${detections.length} item${detections.length === 1 ? '' : 's'} detected`
        )
      }
    } catch (error) {
      console.error(
        'Image detection error:',
        error
      )

      onFeedback?.(
        error.message ||
          'Image detection failed'
      )
    } finally {
      setDetecting(false)
    }
  }

  const detectVideo = async (
    file
  ) => {
    try {
      setDetecting(true)
      setResults([])

      const formData =
        new FormData()

      formData.append(
        'file',
        file
      )

      const response =
        await fetch(
          `${API_BASE}/api/vision/detect-video`,
          {
            method: 'POST',
            body: formData
          }
        )

      if (!response.ok) {
        const errorText =
          await response.text()

        throw new Error(
          errorText ||
            `HTTP ${response.status}`
        )
      }

      const data =
        await response.json()

      const detections =
        Array.isArray(
          data?.detections
        )
          ? data.detections
          : Array.isArray(data)
            ? data
            : []

      setResults(
        detections
      )

      if (detections.length === 0) {
        onFeedback?.(
          'No recognizable inventory item was detected'
        )
      } else {
        onFeedback?.(
          `${detections.length} item${detections.length === 1 ? '' : 's'} detected`
        )
      }
    } catch (error) {
      console.error(
        'Video detection error:',
        error
      )

      onFeedback?.(
        error.message ||
          'Video detection failed'
      )
    } finally {
      setDetecting(false)
    }
  }

  const handleDetect = async () => {
    if (!selectedFile) {
      onFeedback?.(
        'Please select a file first'
      )
      return
    }

    if (
      selectedFile.type.startsWith(
        'video/'
      )
    ) {
      await detectVideo(
        selectedFile
      )
    } else {
      await detectImage(
        selectedFile
      )
    }
  }

  const openAddModal = (
    item
  ) => {
    setSelectedItem(item)
    setQuantity(1)
    setShowQuantityModal(true)
  }

  const addToInventory = async () => {
    if (!selectedItem) {
      return
    }

    try {
      const name =
        selectedItem.name ||
        selectedItem.class_name ||
        selectedItem.label

      if (!name) {
        throw new Error(
          'Detected item does not have a valid name'
        )
      }

      const response =
        await fetch(
          `${API_BASE}/api/inventory/add`,
          {
            method: 'POST',
            headers: {
              'Content-Type':
                'application/json'
            },
            body: JSON.stringify({
              name,
              quantity:
                Number(quantity) || 1
            })
          }
        )

      if (!response.ok) {
        const errorText =
          await response.text()

        throw new Error(
          errorText ||
            `HTTP ${response.status}`
        )
      }

      setShowQuantityModal(
        false
      )

      setSelectedItem(null)

      onFeedback?.(
        `${name} added to inventory`
      )

      await onSuccess?.()
    } catch (error) {
      console.error(
        'Add inventory error:',
        error
      )

      onFeedback?.(
        error.message ||
          'Unable to add item'
      )
    }
  }

  return (
    <>
      <style>{`
        .camera-page {
          width: 100%;
          min-width: 0;
        }

        .camera-heading {
          margin-bottom: 22px;
        }

        .camera-title {
          margin: 0;
          color: #123F40;
          font-size: 28px;
          line-height: 1.2;
          font-weight: 800;
          letter-spacing: -0.7px;
        }

        .camera-description {
          margin: 7px 0 0;
          color: #557879;
          font-size: 12px;
          line-height: 1.5;
        }

        .detector-card {
          width: 100%;
          overflow: hidden;

          background: #FFFFFF;

          border: 1px solid #94C9C5;
          border-radius: 14px;

          box-shadow:
            0 9px 26px rgba(5, 101, 99, 0.10);
        }

        .mode-tabs {
          width: 100%;
          display: grid;
          grid-template-columns:
            repeat(3, 1fr);

          border-bottom: 1px solid #D3E5E3;
        }

        .mode-tab {
          min-height: 58px;

          border: none;
          border-right: 1px solid #D3E5E3;

          background: #FFFFFF;
          color: #547071;

          font-size: 12px;
          font-weight: 650;

          cursor: pointer;

          transition:
            background 0.18s ease,
            color 0.18s ease;
        }

        .mode-tab:last-child {
          border-right: none;
        }

        .mode-tab:hover {
          background: #DDF1EF;
          color: #087F7D;
        }

        .mode-tab.active {
          background: #056563;
          color: #FFFFFF;
        }

        .mode-tab.active:hover {
          background: #044F4D;
          color: #FFFFFF;
        }

        .detector-content {
          padding: 28px;
        }

        .camera-box {
          width: 100%;
          min-height: 330px;

          display: flex;
          align-items: center;
          justify-content: center;

          padding: 25px;

          border: 1px dashed #9FCBC8;
          border-radius: 12px;

          background: #F4FBFA;

          text-align: center;
        }

        .camera-inner {
          width: min(700px, 100%);
        }

        .camera-heading-small {
          margin: 0;

          color: #123F40;

          font-size: 20px;
          font-weight: 750;
        }

        .camera-text {
          margin: 8px 0 20px;

          color: #698183;

          font-size: 12px;
          line-height: 1.5;
        }

        .primary-button {
          min-height: 43px;

          padding: 0 19px;

          border: 1px solid #056563;
          border-radius: 8px;

          background: #056563;
          color: #FFFFFF;

          font-size: 11px;
          font-weight: 750;

          cursor: pointer;

          box-shadow:
            0 5px 12px rgba(5, 101, 99, 0.16);

          transition:
            background 0.18s ease,
            transform 0.18s ease,
            box-shadow 0.18s ease;
        }

        .primary-button:hover {
          background: #044F4D;

          box-shadow:
            0 7px 15px rgba(5, 101, 99, 0.22);
        }

        .primary-button:active {
          transform: translateY(1px);
        }

        .secondary-button {
          min-height: 43px;

          padding: 0 18px;

          border: 1px solid #8FCBC7;
          border-radius: 8px;

          background: #DDF1EF;
          color: #087F7D;

          font-size: 11px;
          font-weight: 750;

          cursor: pointer;
        }

        .camera-video {
          width: 100%;
          max-height: 430px;

          border-radius: 10px;

          background: #064E4C;

          object-fit: cover;
        }

        .button-row {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 9px;
          flex-wrap: wrap;
        }

        .file-input {
          display: none;
        }

        .preview-image,
        .preview-video {
          width: 100%;
          max-height: 430px;

          border-radius: 10px;

          background: #E2F2F0;

          object-fit: contain;
        }

        .preview-wrapper {
          width: 100%;
          margin-bottom: 18px;
        }

        .detect-row {
          display: flex;
          justify-content: center;
          gap: 9px;
          flex-wrap: wrap;
        }

        .results-section {
          margin-top: 22px;

          padding: 20px;

          border: 1px solid #A5CECA;
          border-radius: 12px;

          background: #E1F1EF;
        }

        .results-title {
          margin: 0 0 13px;

          color: #123F40;

          font-size: 15px;
          font-weight: 800;
        }

        .results-grid {
          display: grid;

          grid-template-columns:
            repeat(
              auto-fit,
              minmax(190px, 1fr)
            );

          gap: 10px;
        }

        .result-card {
          padding: 14px;

          border: 1px solid #B8D9D6;
          border-radius: 9px;

          background: #FFFFFF;
        }

        .result-name {
          margin: 0;

          color: #173F40;

          font-size: 12px;
          font-weight: 750;
        }

        .result-confidence {
          margin: 5px 0 12px;

          color: #718788;

          font-size: 10px;
        }

        .result-add {
          width: 100%;
          min-height: 35px;

          border: 1px solid #087F7D;
          border-radius: 7px;

          background: #087F7D;
          color: #FFFFFF;

          font-size: 10px;
          font-weight: 700;

          cursor: pointer;
        }

        .result-add:hover {
          background: #056563;
        }

        /* MODAL */

        .modal-overlay {
          position: fixed;
          inset: 0;

          z-index: 100;

          display: flex;
          align-items: center;
          justify-content: center;

          padding: 20px;

          background:
            rgba(4, 79, 77, 0.45);
        }

        .modal {
          width: min(420px, 100%);

          padding: 24px;

          border-radius: 13px;

          background: #FFFFFF;

          box-shadow:
            0 20px 55px rgba(4, 79, 77, 0.25);
        }

        .modal-title {
          margin: 0;

          color: #123F40;

          font-size: 18px;
          font-weight: 800;
        }

        .modal-description {
          margin: 7px 0 18px;

          color: #6A8182;

          font-size: 11px;
          line-height: 1.5;
        }

        .quantity-input {
          width: 100%;
          height: 42px;

          padding: 0 12px;

          border: 1px solid #A2CECA;
          border-radius: 8px;

          outline: none;

          color: #173F40;
          background: #F8FCFB;

          font-size: 12px;
        }

        .quantity-input:focus {
          border-color: #087F7D;

          box-shadow:
            0 0 0 3px rgba(8, 127, 125, 0.09);
        }

        .modal-actions {
          display: flex;
          justify-content: flex-end;

          gap: 8px;

          margin-top: 18px;
        }

        @media (max-width: 700px) {
          .detector-content {
            padding: 16px;
          }

          .camera-title {
            font-size: 24px;
          }

          .camera-box {
            min-height: 270px;
            padding: 18px;
          }

          .mode-tab {
            min-height: 52px;
            font-size: 11px;
          }

          .results-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 430px) {
          .mode-tab {
            min-height: 48px;
            font-size: 10px;
          }

          .camera-box {
            min-height: 235px;
          }

          .button-row,
          .detect-row {
            flex-direction: column;
            width: 100%;
          }

          .primary-button,
          .secondary-button {
            width: 100%;
          }
        }
      `}</style>

      <div className="camera-page">
        <div className="camera-heading">
          <h2 className="camera-title">
            Object Detection
          </h2>

          <p className="camera-description">
            Detect inventory items using your
            camera, an image, or a video.
          </p>
        </div>

        <section className="detector-card">
          <div className="mode-tabs">
            <button
              type="button"
              className={`mode-tab ${
                activeMode === 'camera'
                  ? 'active'
                  : ''
              }`}
              onClick={() =>
                handleModeChange(
                  'camera'
                )
              }
            >
              Camera
            </button>

            <button
              type="button"
              className={`mode-tab ${
                activeMode === 'image'
                  ? 'active'
                  : ''
              }`}
              onClick={() =>
                handleModeChange(
                  'image'
                )
              }
            >
              Image
            </button>

            <button
              type="button"
              className={`mode-tab ${
                activeMode === 'video'
                  ? 'active'
                  : ''
              }`}
              onClick={() =>
                handleModeChange(
                  'video'
                )
              }
            >
              Video
            </button>
          </div>

          <div className="detector-content">
            {activeMode === 'camera' && (
              <div className="camera-box">
                <div className="camera-inner">
                  {cameraActive ? (
                    <>
                      <video
                        ref={videoRef}
                        className="camera-video"
                        autoPlay
                        muted
                        playsInline
                      />

                      <div
                        className="button-row"
                        style={{
                          marginTop: '15px'
                        }}
                      >
                        <button
                          type="button"
                          className="primary-button"
                          onClick={
                            captureFrame
                          }
                        >
                          Detect Item
                        </button>

                        <button
                          type="button"
                          className="secondary-button"
                          onClick={
                            stopCamera
                          }
                        >
                          Stop Camera
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <h3 className="camera-heading-small">
                        Camera Detection
                      </h3>

                      <p className="camera-text">
                        Start the camera to
                        detect an item and
                        add it to inventory.
                      </p>

                      <button
                        type="button"
                        className="primary-button"
                        onClick={
                          startCamera
                        }
                      >
                        Start Camera
                      </button>
                    </>
                  )}
                </div>
              </div>
            )}

            {activeMode === 'image' && (
              <div className="camera-box">
                <div className="camera-inner">
                  {previewUrl ? (
                    <div className="preview-wrapper">
                      <img
                        src={previewUrl}
                        alt="Selected inventory item"
                        className="preview-image"
                      />
                    </div>
                  ) : (
                    <>
                      <h3 className="camera-heading-small">
                        Image Detection
                      </h3>

                      <p className="camera-text">
                        Select an image to
                        identify an inventory
                        item.
                      </p>
                    </>
                  )}

                  <div className="button-row">
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() =>
                        fileInputRef.current?.click()
                      }
                    >
                      Choose Image
                    </button>

                    {selectedFile && (
                      <button
                        type="button"
                        className="primary-button"
                        onClick={
                          handleDetect
                        }
                        disabled={detecting}
                      >
                        {detecting
                          ? 'Detecting...'
                          : 'Detect Image'}
                      </button>
                    )}
                  </div>

                  <input
                    ref={fileInputRef}
                    className="file-input"
                    type="file"
                    accept="image/*"
                    onChange={
                      handleFileChange
                    }
                  />
                </div>
              </div>
            )}

            {activeMode === 'video' && (
              <div className="camera-box">
                <div className="camera-inner">
                  {previewUrl ? (
                    <div className="preview-wrapper">
                      <video
                        src={previewUrl}
                        className="preview-video"
                        controls
                      />
                    </div>
                  ) : (
                    <>
                      <h3 className="camera-heading-small">
                        Video Detection
                      </h3>

                      <p className="camera-text">
                        Select a video to detect
                        inventory items.
                      </p>
                    </>
                  )}

                  <div className="button-row">
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() =>
                        fileInputRef.current?.click()
                      }
                    >
                      Choose Video
                    </button>

                    {selectedFile && (
                      <button
                        type="button"
                        className="primary-button"
                        onClick={
                          handleDetect
                        }
                        disabled={detecting}
                      >
                        {detecting
                          ? 'Detecting...'
                          : 'Detect Video'}
                      </button>
                    )}
                  </div>

                  <input
                    ref={fileInputRef}
                    className="file-input"
                    type="file"
                    accept="video/*"
                    onChange={
                      handleFileChange
                    }
                  />
                </div>
              </div>
            )}

            {results.length > 0 && (
              <div className="results-section">
                <h3 className="results-title">
                  Detection Results
                </h3>

                <div className="results-grid">
                  {results.map(
                    (item, index) => {
                      const name =
                        item.name ||
                        item.class_name ||
                        item.label ||
                        'Detected item'

                      const confidence =
                        item.confidence

                      return (
                        <div
                          className="result-card"
                          key={`${name}-${index}`}
                        >
                          <p className="result-name">
                            {name}
                          </p>

                          {confidence !==
                            undefined && (
                            <p className="result-confidence">
                              Confidence:{' '}
                              {(
                                Number(
                                  confidence
                                ) * 100
                              ).toFixed(1)}
                              %
                            </p>
                          )}

                          <button
                            type="button"
                            className="result-add"
                            onClick={() =>
                              openAddModal(
                                item
                              )
                            }
                          >
                            Add to Inventory
                          </button>
                        </div>
                      )
                    }
                  )}
                </div>
              </div>
            )}
          </div>
        </section>
      </div>

      {showQuantityModal && (
        <div
          className="modal-overlay"
          onMouseDown={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              setShowQuantityModal(
                false
              )
            }
          }}
        >
          <div className="modal">
            <h3 className="modal-title">
              Add to Inventory
            </h3>

            <p className="modal-description">
              Set the quantity for{' '}
              <strong>
                {selectedItem?.name ||
                  selectedItem?.class_name ||
                  selectedItem?.label ||
                  'this item'}
              </strong>
              .
            </p>

            <input
              className="quantity-input"
              type="number"
              min="1"
              value={quantity}
              onChange={(event) =>
                setQuantity(
                  Math.max(
                    1,
                    Number(
                      event.target.value
                    ) || 1
                  )
                )
              }
            />

            <div className="modal-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() =>
                  setShowQuantityModal(
                    false
                  )
                }
              >
                Cancel
              </button>

              <button
                type="button"
                className="primary-button"
                onClick={
                  addToInventory
                }
              >
                Add Item
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default CameraDetector