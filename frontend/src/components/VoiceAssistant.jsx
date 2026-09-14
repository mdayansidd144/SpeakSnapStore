import {
  useState,
  useRef,
  useEffect
} from 'react'

const API_BASE =
  import.meta.env.VITE_API_URL ||
  'http://localhost:8000'

export default function VoiceAssistant({
  onFeedback,
  onSuccess
}) {
  const [input, setInput] = useState('')
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [multipleItems, setMultipleItems] = useState(null)

  const recognitionRef = useRef(null)
  const listeningRef = useRef(false)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true

    return () => {
      mountedRef.current = false
      listeningRef.current = false

      const recognition = recognitionRef.current

      if (recognition) {
        try {
          recognition.onstart = null
          recognition.onresult = null
          recognition.onerror = null
          recognition.onend = null
          recognition.onnomatch = null
          recognition.stop()
        } catch {
          // Recognition may already be stopped.
        }

        recognitionRef.current = null
      }
    }
  }, [])

  const parseMultipleItems = (text) => {
    const items = []

    const cleanedText = text
      .replace(
        /\b(add|stock|inventory)\b/gi,
        ''
      )
      .trim()

    const pattern =
      /(\d+)\s+([a-zA-Z][a-zA-Z\s-]*?)(?=\s*,|\s+and\s+|\.|$)/gi

    let match

    while (
      (match = pattern.exec(cleanedText)) !== null
    ) {
      const quantity =
        Number.parseInt(match[1], 10)

      const itemName = match[2]
        .trim()
        .replace(/\s+/g, ' ')

      if (
        itemName.length > 1 &&
        Number.isInteger(quantity) &&
        quantity > 0
      ) {
        items.push({
          item: itemName,
          quantity,
          action: 'add'
        })
      }
    }

    return items
  }

  const startVoice = () => {
    if (loading) {
      return
    }

    if (listeningRef.current) {
      return
    }

    if (
      !('webkitSpeechRecognition' in window) &&
      !('SpeechRecognition' in window)
    ) {
      onFeedback(
        'Voice recognition is not supported by this browser.'
      )
      return
    }

    try {
      const SpeechRecognition =
        window.webkitSpeechRecognition ||
        window.SpeechRecognition

      const recognition =
        new SpeechRecognition()

      recognition.continuous = false
      recognition.interimResults = false
      recognition.lang = 'en-US'
      recognition.maxAlternatives = 1

      recognitionRef.current = recognition
      listeningRef.current = true

      recognition.onstart = () => {
        if (!mountedRef.current) {
          return
        }

        setIsListening(true)

        onFeedback(
          'Listening for your inventory command.'
        )
      }

      recognition.onresult = (event) => {
        if (!mountedRef.current) {
          return
        }

        const text =
          event.results?.[0]?.[0]
            ?.transcript
            ?.trim() || ''

        listeningRef.current = false
        setIsListening(false)

        if (text) {
          setInput(text)

          onFeedback(
            'Voice input received.'
          )

          parseCommand(text)
        } else {
          onFeedback(
            'No voice input was detected.'
          )
        }
      }

      recognition.onerror = (event) => {
        const errorType =
          event?.error || 'unknown'

        /*
         * "aborted" is normally produced when recognition
         * is intentionally stopped or the browser ends the
         * recognition session. It should not be treated as
         * an application failure.
         */
        if (errorType === 'aborted') {
          listeningRef.current = false

          if (mountedRef.current) {
            setIsListening(false)
          }

          return
        }

        console.error(
          'Speech recognition error:',
          errorType
        )

        listeningRef.current = false

        if (mountedRef.current) {
          setIsListening(false)

          if (errorType === 'not-allowed') {
            onFeedback(
              'Microphone permission was denied. Allow microphone access and try again.'
            )
          } else if (errorType === 'audio-capture') {
            onFeedback(
              'No microphone could be accessed. Check your microphone settings.'
            )
          } else if (errorType === 'network') {
            onFeedback(
              'Speech recognition could not connect to the browser speech service.'
            )
          } else if (errorType === 'no-speech') {
            onFeedback(
              'No speech was detected. Please try again.'
            )
          } else {
            onFeedback(
              'Voice input could not be processed.'
            )
          }
        }
      }

      recognition.onnomatch = () => {
        listeningRef.current = false

        if (mountedRef.current) {
          setIsListening(false)

          onFeedback(
            'Speech could not be understood. Please try again.'
          )
        }
      }

      recognition.onend = () => {
        listeningRef.current = false

        if (mountedRef.current) {
          setIsListening(false)
        }

        if (recognitionRef.current === recognition) {
          recognitionRef.current = null
        }
      }

      recognition.start()
    } catch (error) {
      console.error(
        'Unable to start speech recognition:',
        error
      )

      listeningRef.current = false
      recognitionRef.current = null

      if (mountedRef.current) {
        setIsListening(false)

        if (
          error?.name ===
          'InvalidStateError'
        ) {
          onFeedback(
            'Voice recognition is already running. Please wait and try again.'
          )
        } else {
          onFeedback(
            'Unable to start voice recognition.'
          )
        }
      }
    }
  }

  const stopVoice = () => {
    const recognition =
      recognitionRef.current

    listeningRef.current = false

    if (recognition) {
      try {
        /*
         * Use stop() for a normal user-initiated stop.
         * abort() causes Chrome to emit the "aborted"
         * error event.
         */
        recognition.stop()
      } catch {
        // Recognition may already be stopped.
      }
    }

    if (mountedRef.current) {
      setIsListening(false)

      onFeedback(
        'Voice input stopped.'
      )
    }
  }

  const parseCommand = async (text) => {
    const cleanedText = text?.trim()

    if (!cleanedText) {
      onFeedback(
        'Enter an inventory command before processing.'
      )
      return
    }

    setLoading(true)
    setMultipleItems(null)
    setPreview(null)

    const hasMultipleItems =
      cleanedText.includes(',') ||
      /\band\b/i.test(cleanedText)

    const parsedMultipleItems =
      parseMultipleItems(cleanedText)

    if (
      hasMultipleItems &&
      parsedMultipleItems.length > 1
    ) {
      setMultipleItems(
        parsedMultipleItems
      )

      setLoading(false)

      onFeedback(
        `${parsedMultipleItems.length} inventory items detected.`
      )

      return
    }

    try {
      const response = await fetch(
        `${API_BASE}/api/parse/`,
        {
          method: 'POST',
          headers: {
            'Content-Type':
              'application/json'
          },
          body: JSON.stringify({
            text: cleanedText
          })
        }
      )

      if (!response.ok) {
        throw new Error(
          `Parse request failed with status ${response.status}`
        )
      }

      const data =
        await response.json()

      if (
        !data?.item ||
        data.item === 'item'
      ) {
        onFeedback(
          'The inventory item could not be identified.'
        )
        return
      }

      if (
        !data?.quantity ||
        Number(data.quantity) <= 0
      ) {
        onFeedback(
          'The inventory quantity could not be identified.'
        )
        return
      }

      setPreview({
        ...data,
        quantity:
          Number(data.quantity),
        item: String(
          data.item
        ).trim(),
        action:
          data.action === 'remove'
            ? 'remove'
            : 'add'
      })

      onFeedback(
        'Review the detected inventory action.'
      )
    } catch (error) {
      console.error(
        'Command parsing failed:',
        error
      )

      onFeedback(
        'The inventory command could not be processed.'
      )
    } finally {
      setLoading(false)
    }
  }

  const confirmAction = async () => {
    if (!preview || loading) {
      return
    }

    const endpoint =
      preview.action === 'add'
        ? '/api/inventory/add'
        : '/api/inventory/remove'

    const actionLabel =
      preview.action === 'add'
        ? 'Adding'
        : 'Removing'

    setLoading(true)

    onFeedback(
      `${actionLabel} ${preview.quantity} units of ${preview.item}.`
    )

    try {
      const response = await fetch(
        `${API_BASE}${endpoint}`,
        {
          method: 'POST',
          headers: {
            'Content-Type':
              'application/json'
          },
          body: JSON.stringify({
            name:
              preview.item.toLowerCase(),
            quantity:
              preview.quantity
          })
        }
      )

      if (!response.ok) {
        throw new Error(
          `Inventory update failed with status ${response.status}`
        )
      }

      const data =
        await response.json()

      onFeedback(
        data?.message ||
        'Inventory updated successfully.'
      )

      setPreview(null)
      setInput('')

      onSuccess()
    } catch (error) {
      console.error(
        'Inventory update failed:',
        error
      )

      onFeedback(
        'The inventory could not be updated.'
      )
    } finally {
      setLoading(false)
    }
  }

  const confirmMultipleItems =
    async () => {
      if (
        !multipleItems ||
        multipleItems.length === 0 ||
        loading
      ) {
        return
      }

      setLoading(true)

      let successCount = 0

      for (const item of multipleItems) {
        try {
          const response = await fetch(
            `${API_BASE}/api/inventory/add`,
            {
              method: 'POST',
              headers: {
                'Content-Type':
                  'application/json'
              },
              body: JSON.stringify({
                name:
                  item.item.toLowerCase(),
                quantity:
                  item.quantity
              })
            }
          )

          if (response.ok) {
            successCount += 1
          }
        } catch (error) {
          console.error(
            `Failed to add ${item.item}:`,
            error
          )
        }
      }

      if (
        successCount ===
        multipleItems.length
      ) {
        onFeedback(
          `${successCount} inventory items were added successfully.`
        )
      } else if (
        successCount > 0
      ) {
        onFeedback(
          `${successCount} of ${multipleItems.length} inventory items were added.`
        )
      } else {
        onFeedback(
          'The inventory items could not be added.'
        )
      }

      setMultipleItems(null)
      setInput('')

      onSuccess()

      setLoading(false)
    }

  const cancelMultipleItems = () => {
    if (loading) {
      return
    }

    setMultipleItems(null)

    onFeedback(
      'The inventory update was cancelled.'
    )
  }

  const cancelAction = () => {
    if (loading) {
      return
    }

    setPreview(null)

    onFeedback(
      'The inventory update was cancelled.'
    )
  }

  const panelStyle = {
    background: '#ffffff',
    border:
      '1px solid #dce8e9',
    borderRadius: '13px',
    overflow: 'hidden',
    boxShadow:
      '0 6px 22px rgba(16, 42, 45, 0.04)'
  }

  const primaryButtonStyle = {
    height: '42px',
    padding: '0 18px',
    border:
      '1px solid #0f766e',
    borderRadius: '8px',
    background: '#0f766e',
    color: '#ffffff',
    fontFamily: 'inherit',
    fontSize: '11px',
    fontWeight: 700,
    cursor: loading
      ? 'not-allowed'
      : 'pointer',
    opacity: loading ? 0.55 : 1
  }

  const secondaryButtonStyle = {
    height: '42px',
    padding: '0 18px',
    border:
      '1px solid #cbdadb',
    borderRadius: '8px',
    background: '#ffffff',
    color: '#365255',
    fontFamily: 'inherit',
    fontSize: '11px',
    fontWeight: 650,
    cursor: loading
      ? 'not-allowed'
      : 'pointer',
    opacity: loading ? 0.55 : 1
  }

  const inputStyle = {
    width: '100%',
    height: '44px',
    boxSizing: 'border-box',
    padding: '0 13px',
    border:
      '1px solid #d1dfe0',
    borderRadius: '8px',
    background: '#fbfdfd',
    color: '#172a2d',
    fontFamily: 'inherit',
    fontSize: '12px',
    outline: 'none'
  }

  return (
    <div
      style={{
        width: '100%',
        color: '#172a2d',
        fontFamily:
          'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
      }}
    >
      <div
        style={{
          marginBottom: '22px'
        }}
      >
        <div
          style={{
            display: 'inline-flex',
            padding: '5px 8px',
            marginBottom: '9px',
            borderRadius: '5px',
            background: '#e5f5f3',
            color: '#0f766e',
            fontSize: '9px',
            fontWeight: 750,
            textTransform: 'uppercase',
            letterSpacing: '0.55px'
          }}
        >
          Intelligent input
        </div>

        <h2
          style={{
            margin: 0,
            color: '#102a2d',
            fontSize: '24px',
            lineHeight: 1.2,
            fontWeight: 750,
            letterSpacing: '-0.5px'
          }}
        >
          Voice Inventory
        </h2>

        <p
          style={{
            margin: '7px 0 0',
            color: '#718184',
            fontSize: '12px',
            lineHeight: 1.5
          }}
        >
          Add or remove inventory using
          voice commands or manual input.
        </p>
      </div>

      <div style={panelStyle}>
        <div
          style={{
            padding: '27px 30px',
            background: '#f5faf9',
            borderBottom:
              '1px solid #dfeaea'
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent:
                'space-between',
              alignItems: 'center',
              gap: '20px',
              flexWrap: 'wrap'
            }}
          >
            <div>
              <div
                style={{
                  color: '#102a2d',
                  fontSize: '15px',
                  fontWeight: 750,
                  marginBottom: '5px'
                }}
              >
                Voice command
              </div>

              <div
                style={{
                  color: '#718184',
                  fontSize: '11px',
                  lineHeight: 1.5
                }}
              >
                Speak naturally and review
                the detected action before
                updating stock.
              </div>
            </div>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '9px'
              }}
            >
              <span
                style={{
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  background:
                    isListening
                      ? '#14b8a6'
                      : loading
                        ? '#3b82f6'
                        : '#9aabad',
                  flexShrink: 0
                }}
              />

              <span
                style={{
                  color: isListening
                    ? '#0f766e'
                    : loading
                      ? '#2563eb'
                      : '#718184',
                  fontSize: '10px',
                  fontWeight: 700
                }}
              >
                {isListening
                  ? 'Listening'
                  : loading
                    ? 'Processing'
                    : 'Ready'}
              </span>
            </div>
          </div>

          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              marginTop: '22px'
            }}
          >
            <button
              type="button"
              onClick={
                isListening
                  ? stopVoice
                  : startVoice
              }
              disabled={loading}
              style={{
                ...primaryButtonStyle,
                minWidth: '180px',
                height: '44px',
                background:
                  isListening
                    ? '#2563eb'
                    : '#0f766e',
                borderColor:
                  isListening
                    ? '#2563eb'
                    : '#0f766e'
              }}
            >
              {isListening
                ? 'Stop Listening'
                : 'Start Listening'}
            </button>
          </div>
        </div>

        <div
          style={{
            padding: '24px 30px'
          }}
        >
          <div
            style={{
              marginBottom: '10px'
            }}
          >
            <label
              htmlFor="inventory-command"
              style={{
                color: '#263f42',
                fontSize: '11px',
                fontWeight: 750
              }}
            >
              Manual command
            </label>

            <p
              style={{
                margin: '4px 0 0',
                color: '#819092',
                fontSize: '10px'
              }}
            >
              Enter the inventory request
              you want the system to process.
            </p>
          </div>

          <div
            style={{
              display: 'flex',
              gap: '9px',
              alignItems: 'stretch'
            }}
          >
            <input
              id="inventory-command"
              type="text"
              value={input}
              onChange={(event) =>
                setInput(
                  event.target.value
                )
              }
              onKeyDown={(event) => {
                if (
                  event.key === 'Enter' &&
                  !loading &&
                  input.trim()
                ) {
                  parseCommand(input)
                }
              }}
              placeholder="Enter inventory command"
              disabled={loading}
              autoComplete="off"
              style={{
                ...inputStyle,
                flex: 1,
                minWidth: 0
              }}
            />

            <button
              type="button"
              onClick={() =>
                parseCommand(input)
              }
              disabled={
                loading ||
                !input.trim()
              }
              style={{
                ...primaryButtonStyle,
                minWidth: '100px'
              }}
            >
              {loading
                ? 'Processing'
                : 'Process'}
            </button>
          </div>
        </div>

        {multipleItems && (
          <div
            style={{
              padding: '24px 30px',
              borderTop:
                '1px solid #e5eeee',
              background: '#fbfdfd'
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent:
                  'space-between',
                alignItems: 'flex-start',
                gap: '15px',
                marginBottom: '14px'
              }}
            >
              <div>
                <div
                  style={{
                    display: 'inline-flex',
                    padding: '4px 7px',
                    marginBottom: '7px',
                    borderRadius: '4px',
                    background: '#edf4ff',
                    color: '#2563eb',
                    fontSize: '8px',
                    fontWeight: 750,
                    textTransform:
                      'uppercase',
                    letterSpacing: '0.45px'
                  }}
                >
                  Multiple items
                </div>

                <h3
                  style={{
                    margin: 0,
                    color: '#203a3d',
                    fontSize: '15px',
                    fontWeight: 750
                  }}
                >
                  Review detected items
                </h3>
              </div>

              <div
                style={{
                  padding: '5px 8px',
                  borderRadius: '6px',
                  background: '#e5f5f3',
                  color: '#0f766e',
                  fontSize: '9px',
                  fontWeight: 750
                }}
              >
                {multipleItems.length}{' '}
                items
              </div>
            </div>

            <div
              style={{
                border:
                  '1px solid #dce7e8',
                borderRadius: '9px',
                overflow: 'hidden',
                background: '#ffffff'
              }}
            >
              {multipleItems.map(
                (item, index) => (
                  <div
                    key={`${item.item}-${index}`}
                    style={{
                      display: 'flex',
                      justifyContent:
                        'space-between',
                      alignItems: 'center',
                      gap: '16px',
                      padding: '13px 14px',
                      borderBottom:
                        index ===
                        multipleItems.length - 1
                          ? 'none'
                          : '1px solid #edf1f1'
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        minWidth: 0
                      }}
                    >
                      <div
                        style={{
                          width: '29px',
                          height: '29px',
                          borderRadius: '7px',
                          background: '#e9f6f4',
                          color: '#0f766e',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                          fontSize: '8px',
                          fontWeight: 800
                        }}
                      >
                        {String(
                          item.item || 'IT'
                        )
                          .slice(0, 2)
                          .toUpperCase()}
                      </div>

                      <span
                        style={{
                          color: '#263f42',
                          fontSize: '12px',
                          fontWeight: 650,
                          overflowWrap:
                            'anywhere'
                        }}
                      >
                        {item.item}
                      </span>
                    </div>

                    <span
                      style={{
                        flexShrink: 0,
                        padding: '5px 8px',
                        borderRadius: '5px',
                        background: '#f3f7f7',
                        color: '#52696c',
                        fontSize: '10px',
                        fontWeight: 700
                      }}
                    >
                      {item.quantity}{' '}
                      units
                    </span>
                  </div>
                )
              )}
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: '8px',
                marginTop: '16px'
              }}
            >
              <button
                type="button"
                onClick={
                  cancelMultipleItems
                }
                disabled={loading}
                style={
                  secondaryButtonStyle
                }
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={
                  confirmMultipleItems
                }
                disabled={loading}
                style={
                  primaryButtonStyle
                }
              >
                {loading
                  ? 'Updating'
                  : 'Add Items'}
              </button>
            </div>
          </div>
        )}

        {preview && (
          <div
            style={{
              padding: '24px 30px',
              borderTop:
                '1px solid #e5eeee',
              background: '#fbfdfd'
            }}
          >
            <div
              style={{
                display: 'inline-flex',
                padding: '4px 7px',
                marginBottom: '7px',
                borderRadius: '4px',
                background:
                  preview.action === 'add'
                    ? '#e5f5f3'
                    : '#edf4ff',
                color:
                  preview.action === 'add'
                    ? '#0f766e'
                    : '#2563eb',
                fontSize: '8px',
                fontWeight: 750,
                textTransform:
                  'uppercase',
                letterSpacing: '0.45px'
              }}
            >
              {preview.action === 'add'
                ? 'Add stock'
                : 'Remove stock'}
            </div>

            <h3
              style={{
                margin: '0 0 15px',
                color: '#203a3d',
                fontSize: '15px',
                fontWeight: 750
              }}
            >
              Review inventory update
            </h3>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns:
                  '130px 1fr',
                border:
                  '1px solid #dce7e8',
                borderRadius: '9px',
                overflow: 'hidden',
                background: '#ffffff'
              }}
            >
              <div
                style={{
                  padding: '12px 14px',
                  background: '#f4f8f8',
                  color: '#718184',
                  fontSize: '9px',
                  fontWeight: 750,
                  textTransform:
                    'uppercase',
                  letterSpacing: '0.45px',
                  borderBottom:
                    '1px solid #e5eeee'
                }}
              >
                Item
              </div>

              <div
                style={{
                  padding: '12px 14px',
                  color: '#203a3d',
                  fontSize: '12px',
                  fontWeight: 650,
                  overflowWrap: 'anywhere',
                  borderBottom:
                    '1px solid #e5eeee'
                }}
              >
                {preview.item}
              </div>

              <div
                style={{
                  padding: '12px 14px',
                  background: '#f4f8f8',
                  color: '#718184',
                  fontSize: '9px',
                  fontWeight: 750,
                  textTransform:
                    'uppercase',
                  letterSpacing: '0.45px',
                  borderBottom:
                    '1px solid #e5eeee'
                }}
              >
                Action
              </div>

              <div
                style={{
                  padding: '12px 14px',
                  color:
                    preview.action === 'add'
                      ? '#0f766e'
                      : '#2563eb',
                  fontSize: '12px',
                  fontWeight: 750,
                  borderBottom:
                    '1px solid #e5eeee'
                }}
              >
                {preview.action === 'add'
                  ? 'Add stock'
                  : 'Remove stock'}
              </div>

              <div
                style={{
                  padding: '12px 14px',
                  background: '#f4f8f8',
                  color: '#718184',
                  fontSize: '9px',
                  fontWeight: 750,
                  textTransform:
                    'uppercase',
                  letterSpacing: '0.45px'
                }}
              >
                Quantity
              </div>

              <div
                style={{
                  padding: '12px 14px',
                  color: '#203a3d',
                  fontSize: '12px',
                  fontWeight: 700
                }}
              >
                {preview.quantity}{' '}
                units
              </div>
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: '8px',
                marginTop: '16px'
              }}
            >
              <button
                type="button"
                onClick={cancelAction}
                disabled={loading}
                style={
                  secondaryButtonStyle
                }
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={confirmAction}
                disabled={loading}
                style={
                  primaryButtonStyle
                }
              >
                {loading
                  ? 'Updating'
                  : 'Confirm Update'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}