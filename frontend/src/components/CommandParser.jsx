import {
  useState,
  useCallback,
  useEffect,
  useRef
} from 'react'

const API_BASE =
  import.meta.env.VITE_API_URL ||
  'http://localhost:8000'

export default function CommandParser({
  onParsed,
  onFeedback,
  onLoading,
  onSuccess
}) {
  const [input, setInput] = useState('')
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])
  const [historyIndex, setHistoryIndex] =
    useState(-1)

  const inputRef = useRef(null)

  useEffect(() => {
    try {
      const savedHistory =
        localStorage.getItem(
          'commandHistory'
        )

      if (savedHistory) {
        const parsed =
          JSON.parse(savedHistory)

        if (Array.isArray(parsed)) {
          setHistory(parsed)
        }
      }
    } catch (error) {
      console.error(
        'Failed to load command history:',
        error
      )
    }

    inputRef.current?.focus()
  }, [])

  const saveToHistory = useCallback(
    (command) => {
      const trimmedCommand =
        command.trim()

      if (!trimmedCommand) {
        return
      }

      setHistory((previous) => {
        const newHistory = [
          trimmedCommand,
          ...previous.filter(
            (item) =>
              item !== trimmedCommand
          )
        ].slice(0, 20)

        try {
          localStorage.setItem(
            'commandHistory',
            JSON.stringify(newHistory)
          )
        } catch (error) {
          console.error(
            'Failed to save command history:',
            error
          )
        }

        return newHistory
      })

      setHistoryIndex(-1)
    },
    []
  )

  const parseCommand = useCallback(
    async (text) => {
      const trimmedText =
        text?.trim()

      if (!trimmedText) {
        onFeedback?.(
          'Please enter a command.'
        )
        return null
      }

      setLoading(true)
      onLoading?.(true)

      onFeedback?.(
        'Processing your command.'
      )

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
              text: trimmedText
            })
          }
        )

        if (!response.ok) {
          let message =
            'Unable to parse the command.'

          try {
            const errorData =
              await response.json()

            if (
              typeof errorData?.detail ===
              'string'
            ) {
              message =
                errorData.detail
            }
          } catch {
            // Ignore JSON parsing errors.
          }

          throw new Error(message)
        }

        const data =
          await response.json()

        const item =
          String(data?.item || '')
            .trim()

        const parsedQuantity =
          Number.parseInt(
            data?.quantity,
            10
          )

        const action =
          data?.action === 'remove'
            ? 'remove'
            : 'add'

        if (
          !item ||
          item.toLowerCase() ===
            'item'
        ) {
          onFeedback?.(
            'Could not identify the inventory item.'
          )
          return null
        }

        if (
          !Number.isInteger(
            parsedQuantity
          ) ||
          parsedQuantity <= 0
        ) {
          onFeedback?.(
            'Could not identify a valid quantity.'
          )
          return null
        }

        const parsedData = {
          item,
          quantity: parsedQuantity,
          action,
          originalText: trimmedText
        }

        setPreview(parsedData)

        onParsed?.(parsedData)

        onFeedback?.(
          'Command parsed successfully. Review the details before confirming.'
        )

        return parsedData
      } catch (error) {
        console.error(
          'Command parsing failed:',
          error
        )

        onFeedback?.(
          error?.message ||
            'Error parsing command.'
        )

        return null
      } finally {
        setLoading(false)
        onLoading?.(false)
      }
    },
    [
      onFeedback,
      onParsed,
      onLoading
    ]
  )

  const confirmAction =
    useCallback(async () => {
      if (!preview) {
        return null
      }

      const endpoint =
        preview.action === 'add'
          ? '/api/inventory/add'
          : '/api/inventory/remove'

      setLoading(true)
      onLoading?.(true)

      onFeedback?.(
        preview.action === 'add'
          ? 'Adding item to inventory.'
          : 'Removing item from inventory.'
      )

      try {
        const response =
          await fetch(
            `${API_BASE}${endpoint}`,
            {
              method: 'POST',
              headers: {
                'Content-Type':
                  'application/json'
              },
              body: JSON.stringify({
                name: preview.item
                  .trim()
                  .toLowerCase(),
                quantity:
                  preview.quantity
              })
            }
          )

        let data = null

        try {
          data =
            await response.json()
        } catch {
          data = null
        }

        if (!response.ok) {
          const message =
            typeof data?.detail ===
            'string'
              ? data.detail
              : typeof data?.message ===
                'string'
                ? data.message
                : 'Inventory operation failed.'

          throw new Error(message)
        }

        onFeedback?.(
          data?.message ||
            'Inventory updated successfully.'
        )

        saveToHistory(
          preview.originalText
        )

        setPreview(null)
        setInput('')
        setHistoryIndex(-1)

        onSuccess?.()

        return data
      } catch (error) {
        console.error(
          'Inventory operation failed:',
          error
        )

        onFeedback?.(
          error?.message ||
            'Failed to update inventory.'
        )

        return null
      } finally {
        setLoading(false)
        onLoading?.(false)
      }
    }, [
      preview,
      onFeedback,
      onLoading,
      saveToHistory,
      onSuccess
    ])

  const cancelAction =
    useCallback(() => {
      if (loading) {
        return
      }

      setPreview(null)

      onFeedback?.(
        'Action cancelled.'
      )
    }, [loading, onFeedback])

  const handleKeyDown =
    useCallback(
      (event) => {
        if (
          event.key === 'Enter' &&
          !event.shiftKey
        ) {
          event.preventDefault()

          if (!loading) {
            parseCommand(input)
          }

          return
        }

        if (
          event.key === 'ArrowUp' &&
          history.length > 0
        ) {
          event.preventDefault()

          const newIndex =
            historyIndex + 1

          if (
            newIndex <
            history.length
          ) {
            setHistoryIndex(
              newIndex
            )
            setInput(
              history[newIndex]
            )
          }

          return
        }

        if (
          event.key === 'ArrowDown' &&
          historyIndex > -1
        ) {
          event.preventDefault()

          const newIndex =
            historyIndex - 1

          setHistoryIndex(
            newIndex
          )

          setInput(
            newIndex === -1
              ? ''
              : history[newIndex]
          )
        }
      },
      [
        input,
        history,
        historyIndex,
        loading,
        parseCommand
      ]
    )

  const clearHistory = () => {
    if (loading) {
      return
    }

    setHistory([])
    setHistoryIndex(-1)

    try {
      localStorage.removeItem(
        'commandHistory'
      )
    } catch (error) {
      console.error(
        'Failed to clear command history:',
        error
      )
    }

    onFeedback?.(
      'Command history cleared.'
    )
  }

  const inputStyle = {
    flex: 1,
    minWidth: 0,
    height: '44px',
    padding: '0 13px',
    border:
      '1px solid #d9d9d9',
    borderRadius: '7px',
    outline: 'none',
    background: '#ffffff',
    color: '#222222',
    fontFamily: 'inherit',
    fontSize: '13px',
    boxSizing: 'border-box'
  }

  const primaryButtonStyle = {
    height: '44px',
    padding: '0 18px',
    border:
      '1px solid #222222',
    borderRadius: '7px',
    background: '#222222',
    color: '#ffffff',
    fontFamily: 'inherit',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    whiteSpace: 'nowrap'
  }

  const secondaryButtonStyle = {
    height: '40px',
    padding: '0 15px',
    border:
      '1px solid #d8d8d8',
    borderRadius: '7px',
    background: '#ffffff',
    color: '#333333',
    fontFamily: 'inherit',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer'
  }

  const disabledButtonStyle = {
    opacity: 0.5,
    cursor: 'not-allowed'
  }

  return (
    <div
      style={{
        width: '100%',
        maxWidth: '800px',
        margin: '0 auto',
        color: '#222222',
        fontFamily:
          'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
      }}
    >
      <div
        style={{
          marginBottom: '18px'
        }}
      >
        <div
          style={{
            display: 'flex',
            gap: '10px',
            alignItems: 'center'
          }}
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(event) =>
              setInput(
                event.target.value
              )
            }
            onKeyDown={
              handleKeyDown
            }
            placeholder="Enter inventory command"
            disabled={loading}
            style={inputStyle}
            aria-label="Inventory command"
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
              ...(loading ||
              !input.trim()
                ? disabledButtonStyle
                : {})
            }}
          >
            {loading
              ? 'Processing'
              : 'Parse'}
          </button>
        </div>

        {history.length > 0 && (
          <div
            style={{
              display: 'flex',
              justifyContent:
                'space-between',
              alignItems: 'center',
              gap: '12px',
              marginTop: '10px'
            }}
          >
            <span
              style={{
                fontSize: '11px',
                color: '#777777'
              }}
            >
              {history.length}{' '}
              previous commands. Use the arrow keys to navigate.
            </span>

            <button
              type="button"
              onClick={
                clearHistory
              }
              disabled={loading}
              style={{
                ...secondaryButtonStyle,
                height: '32px',
                padding:
                  '0 11px',
                fontSize: '11px',
                ...(loading
                  ? disabledButtonStyle
                  : {})
              }}
            >
              Clear History
            </button>
          </div>
        )}
      </div>

      {preview && (
        <div
          style={{
            marginTop: '20px',
            padding: '20px',
            background: '#ffffff',
            border:
              '1px solid #dddddd',
            borderRadius: '10px'
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent:
                'space-between',
              alignItems: 'center',
              gap: '12px',
              paddingBottom: '14px',
              borderBottom:
                '1px solid #eeeeee'
            }}
          >
            <h3
              style={{
                margin: 0,
                fontSize: '15px',
                fontWeight: 650
              }}
            >
              Command Preview
            </h3>

            <button
              type="button"
              onClick={
                cancelAction
              }
              disabled={loading}
              aria-label="Close preview"
              style={{
                width: '32px',
                height: '32px',
                padding: 0,
                border:
                  '1px solid #d8d8d8',
                borderRadius: '7px',
                background:
                  '#ffffff',
                color: '#444444',
                fontFamily:
                  'inherit',
                fontSize: '14px',
                fontWeight: 600,
                cursor:
                  loading
                    ? 'not-allowed'
                    : 'pointer',
                opacity: loading
                  ? 0.5
                  : 1
              }}
            >
              Close
            </button>
          </div>

          <div
            style={{
              marginTop: '6px'
            }}
          >
            <div
              style={{
                display: 'grid',
                gridTemplateColumns:
                  '110px minmax(0, 1fr)',
                gap: '10px',
                padding:
                  '11px 0',
                borderBottom:
                  '1px solid #eeeeee'
              }}
            >
              <span
                style={{
                  color: '#777777',
                  fontSize: '12px',
                  fontWeight: 600
                }}
              >
                Command
              </span>

              <span
                style={{
                  color: '#222222',
                  fontSize: '13px',
                  overflowWrap:
                    'anywhere'
                }}
              >
                {preview.originalText}
              </span>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns:
                  '110px minmax(0, 1fr)',
                gap: '10px',
                padding:
                  '11px 0',
                borderBottom:
                  '1px solid #eeeeee'
              }}
            >
              <span
                style={{
                  color: '#777777',
                  fontSize: '12px',
                  fontWeight: 600
                }}
              >
                Action
              </span>

              <span
                style={{
                  display:
                    'inline-flex',
                  width: 'fit-content',
                  padding:
                    '5px 9px',
                  border:
                    '1px solid #d8d8d8',
                  borderRadius:
                    '5px',
                  background:
                    '#f7f7f7',
                  color:
                    '#222222',
                  fontSize: '11px',
                  fontWeight: 700
                }}
              >
                {preview.action ===
                'add'
                  ? 'ADD'
                  : 'REMOVE'}
              </span>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns:
                  '110px minmax(0, 1fr)',
                gap: '10px',
                padding:
                  '11px 0',
                borderBottom:
                  '1px solid #eeeeee'
              }}
            >
              <span
                style={{
                  color: '#777777',
                  fontSize: '12px',
                  fontWeight: 600
                }}
              >
                Quantity
              </span>

              <strong
                style={{
                  fontSize: '13px',
                  fontWeight: 650
                }}
              >
                {preview.quantity}
              </strong>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns:
                  '110px minmax(0, 1fr)',
                gap: '10px',
                padding:
                  '11px 0'
              }}
            >
              <span
                style={{
                  color: '#777777',
                  fontSize: '12px',
                  fontWeight: 600
                }}
              >
                Item
              </span>

              <strong
                style={{
                  fontSize: '13px',
                  fontWeight: 650,
                  overflowWrap:
                    'anywhere'
                }}
              >
                {preview.item}
              </strong>
            </div>
          </div>

          <div
            style={{
              display: 'flex',
              justifyContent:
                'flex-end',
              gap: '8px',
              marginTop: '18px'
            }}
          >
            <button
              type="button"
              onClick={
                cancelAction
              }
              disabled={loading}
              style={{
                ...secondaryButtonStyle,
                ...(loading
                  ? disabledButtonStyle
                  : {})
              }}
            >
              Cancel
            </button>

            <button
              type="button"
              onClick={
                confirmAction
              }
              disabled={loading}
              style={{
                ...primaryButtonStyle,
                height: '40px',
                ...(loading
                  ? disabledButtonStyle
                  : {})
              }}
            >
              {loading
                ? 'Processing'
                : 'Confirm'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}