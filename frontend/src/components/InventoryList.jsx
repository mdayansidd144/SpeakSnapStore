import {
  useState,
  useCallback,
  useMemo
} from 'react'

const API_BASE =
  import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function InventoryList({
  inventory,
  onFeedback,
  onSuccess
}) {
  const [searchTerm, setSearchTerm] =
    useState('')

  const [actionItem, setActionItem] =
    useState(null)

  const [actionType, setActionType] =
    useState(null)

  const [quantity, setQuantity] =
    useState('1')

  const [loading, setLoading] =
    useState(false)

  const [optimisticUpdate, setOptimisticUpdate] =
    useState(null)

  const filteredInventory = useMemo(() => {
    if (!Array.isArray(inventory)) {
      return []
    }

    const search =
      searchTerm.trim().toLowerCase()

    if (!search) {
      return inventory
    }

    return inventory.filter((item) =>
      String(item.name || '')
        .toLowerCase()
        .includes(search)
    )
  }, [inventory, searchTerm])

  const totalValue = useMemo(() => {
    if (!Array.isArray(inventory)) {
      return 0
    }

    return inventory.reduce(
      (sum, item) =>
        sum +
        Number(
          item.total_value ??
            ((item.quantity || 0) *
              (item.price || 0))
        ),
      0
    )
  }, [inventory])

  const openActionModal = useCallback(
    (item, type) => {
      setActionItem(item)
      setActionType(type)
      setQuantity(
        type === 'delete'
          ? String(item.quantity || 0)
          : '1'
      )
    },
    []
  )

  const closeActionModal = useCallback(() => {
    if (loading) {
      return
    }

    setActionItem(null)
    setActionType(null)
    setQuantity('1')
  }, [loading])

  const executeAction = useCallback(async () => {
    if (!actionItem || !actionType) {
      return
    }

    const currentQuantity =
      Number(actionItem.quantity || 0)

    let requestedQuantity

    if (actionType === 'delete') {
      requestedQuantity = currentQuantity
    } else {
      requestedQuantity = Number.parseInt(
        quantity,
        10
      )
    }

    if (
      !Number.isInteger(
        requestedQuantity
      ) ||
      requestedQuantity <= 0
    ) {
      onFeedback(
        'Please enter a valid positive quantity.'
      )
      return
    }

    if (
      actionType === 'remove' &&
      requestedQuantity > currentQuantity
    ) {
      onFeedback(
        `Only ${currentQuantity} units are available.`
      )
      return
    }

    const isAdd =
      actionType === 'add'

    const newQuantity = isAdd
      ? currentQuantity + requestedQuantity
      : currentQuantity - requestedQuantity

    setOptimisticUpdate({
      name: actionItem.name,
      newQuantity
    })

    setLoading(true)

    const endpoint = isAdd
      ? '/api/inventory/add'
      : '/api/inventory/remove'

    const actionLabel = isAdd
      ? 'Adding'
      : actionType === 'delete'
        ? 'Deleting'
        : 'Removing'

    onFeedback(
      `${actionLabel} ${requestedQuantity} units of ${actionItem.name}.`
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
            name: actionItem.name.toLowerCase(),
            quantity: requestedQuantity
          })
        }
      )

      if (!response.ok) {
        let message =
          'Inventory update failed.'

        try {
          const errorData =
            await response.json()

          message =
            errorData?.detail ||
            errorData?.message ||
            message
        } catch {
          // Keep default message.
        }

        throw new Error(message)
      }

      const data =
        await response.json()

      onFeedback(
        data?.message ||
          `Inventory updated successfully.`
      )

      setActionItem(null)
      setActionType(null)
      setQuantity('1')
      setOptimisticUpdate(null)

      await onSuccess()
    } catch (error) {
      console.error(
        'Inventory action failed:',
        error
      )

      setOptimisticUpdate(null)

      onFeedback(
        error.message ||
          'The inventory could not be updated.'
      )
    } finally {
      setLoading(false)
    }
  }, [
    actionItem,
    actionType,
    quantity,
    onFeedback,
    onSuccess
  ])

  const getDisplayQuantity = (item) => {
    if (
      optimisticUpdate?.name === item.name
    ) {
      return optimisticUpdate.newQuantity
    }

    return item.quantity
  }

  const getDisplayValue = (item) => {
    const displayQuantity =
      getDisplayQuantity(item)

    return (
      Number(displayQuantity || 0) *
      Number(item.price || 0)
    )
  }

  const clearSearch = () => {
    setSearchTerm('')
    onFeedback('Search cleared.')
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat(
      'en-IN',
      {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 2
      }
    ).format(Number(value || 0))
  }

  const colors = {
    blue: '#0078D4',
    darkBlue: '#005A9E',
    deepBlue: '#004578',
    page: '#C7E2F2',
    light: '#E7F3FB',
    border: '#B8D5E5',
    text: '#12344A',
    muted: '#557387'
  }

  if (
    (!inventory ||
      inventory.length === 0) &&
    !optimisticUpdate
  ) {
    return (
      <section
        style={{
          background: '#FFFFFF',
          border:
            '1px solid #B8D5E5',
          borderRadius: '10px',
          padding: '42px 24px',
          textAlign: 'center'
        }}
      >
        <h3
          style={{
            margin: 0,
            color: colors.deepBlue,
            fontSize: '18px',
            fontWeight: 700
          }}
        >
          Inventory
        </h3>

        <p
          style={{
            margin: '9px 0 0',
            color: colors.muted,
            fontSize: '13px'
          }}
        >
          No items are currently in inventory.
        </p>

        <p
          style={{
            margin: '5px 0 0',
            color: '#7890A0',
            fontSize: '12px'
          }}
        >
          Add items using the Voice or Camera tools.
        </p>
      </section>
    )
  }

  return (
    <>
      <section
        style={{
          background: '#FFFFFF',
          border:
            '1px solid #B8D5E5',
          borderRadius: '10px',
          overflow: 'hidden',
          marginBottom: '20px'
        }}
      >
        <div
          style={{
            padding: '19px 22px',
            borderBottom:
              '1px solid #DCEAF2',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            flexWrap: 'wrap'
          }}
        >
          <div>
            <h3
              style={{
                margin: 0,
                color: colors.deepBlue,
                fontSize: '18px',
                fontWeight: 700
              }}
            >
              Inventory
            </h3>

            <p
              style={{
                margin: '6px 0 0',
                color: colors.muted,
                fontSize: '12px'
              }}
            >
              Manage quantities and monitor inventory value.
            </p>
          </div>

          <div
            style={{
              display: 'flex',
              gap: '8px',
              flexWrap: 'wrap'
            }}
          >
            <span
              style={{
                padding: '7px 11px',
                background: colors.light,
                border:
                  '1px solid #C5DDEB',
                borderRadius: '7px',
                color: colors.darkBlue,
                fontSize: '12px',
                fontWeight: 650
              }}
            >
              {inventory.length} items
            </span>

            <span
              style={{
                padding: '7px 11px',
                background: '#EEF8F2',
                border:
                  '1px solid #C8E3D2',
                borderRadius: '7px',
                color: '#176B3A',
                fontSize: '12px',
                fontWeight: 650
              }}
            >
              {formatCurrency(totalValue)}
            </span>
          </div>
        </div>

        <div
          style={{
            padding: '16px 22px',
            borderBottom:
              '1px solid #DCEAF2',
            display: 'flex',
            gap: '8px'
          }}
        >
          <input
            type="text"
            value={searchTerm}
            onChange={(event) =>
              setSearchTerm(
                event.target.value
              )
            }
            placeholder="Search inventory"
            style={{
              flex: 1,
              minWidth: 0,
              height: '42px',
              boxSizing: 'border-box',
              padding: '0 13px',
              border:
                '1px solid #C2D9E6',
              borderRadius: '7px',
              background: '#FFFFFF',
              color: colors.text,
              fontFamily: 'inherit',
              fontSize: '13px',
              outline: 'none'
            }}
          />

          {searchTerm && (
            <button
              type="button"
              onClick={clearSearch}
              style={{
                height: '42px',
                padding: '0 14px',
                border:
                  '1px solid #C2D9E6',
                borderRadius: '7px',
                background: colors.light,
                color: colors.darkBlue,
                fontFamily: 'inherit',
                fontSize: '12px',
                fontWeight: 650,
                cursor: 'pointer'
              }}
            >
              Clear
            </button>
          )}
        </div>

        <div
          style={{
            padding: '6px 22px 20px'
          }}
        >
          {filteredInventory.length === 0 ? (
            <div
              style={{
                padding: '30px 0',
                textAlign: 'center',
                color: colors.muted,
                fontSize: '13px'
              }}
            >
              No inventory items match your search.
            </div>
          ) : (
            filteredInventory.map((item) => {
              const displayQuantity =
                getDisplayQuantity(item)

              const displayValue =
                getDisplayValue(item)

              const isUpdating =
                optimisticUpdate?.name ===
                item.name

              const isLowStock =
                Number(item.quantity || 0) <= 5

              return (
                <div
                  key={
                    item.id ||
                    item.name
                  }
                  style={{
                    display: 'grid',
                    gridTemplateColumns:
                      'minmax(220px, 1fr) auto auto',
                    alignItems: 'center',
                    gap: '20px',
                    padding: '17px 0',
                    borderBottom:
                      '1px solid #DCEAF2',
                    opacity:
                      isUpdating ? 0.65 : 1
                  }}
                >
                  <div
                    style={{
                      minWidth: 0
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        flexWrap: 'wrap'
                      }}
                    >
                      <span
                        style={{
                          color: colors.text,
                          fontSize: '14px',
                          fontWeight: 700,
                          textTransform:
                            'capitalize',
                          overflowWrap:
                            'anywhere'
                        }}
                      >
                        {item.name}
                      </span>

                      {isLowStock && (
                        <span
                          style={{
                            padding:
                              '3px 7px',
                            background:
                              '#FFF4E5',
                            border:
                              '1px solid #F2D19B',
                            borderRadius:
                              '5px',
                            color:
                              '#9A5B00',
                            fontSize:
                              '10px',
                            fontWeight:
                              700
                          }}
                        >
                          Low stock
                        </span>
                      )}
                    </div>

                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        marginTop: '6px',
                        flexWrap: 'wrap'
                      }}
                    >
                      <span
                        style={{
                          color:
                            colors.muted,
                          fontSize:
                            '11px'
                        }}
                      >
                        {item.category ||
                          'Uncategorized'}
                      </span>

                      <span
                        style={{
                          color:
                            '#7890A0',
                          fontSize:
                            '11px'
                        }}
                      >
                        {formatCurrency(
                          item.price || 0
                        )}{' '}
                        / unit
                      </span>
                    </div>
                  </div>

                  <div
                    style={{
                      textAlign: 'right',
                      minWidth: '105px'
                    }}
                  >
                    <div
                      style={{
                        color:
                          colors.darkBlue,
                        fontSize:
                          '14px',
                        fontWeight:
                          700
                      }}
                    >
                      {displayQuantity}{' '}
                      {item.unit ||
                        'units'}
                    </div>

                    <div
                      style={{
                        marginTop:
                          '4px',
                        color:
                          colors.muted,
                        fontSize:
                          '11px'
                      }}
                    >
                      {formatCurrency(
                        displayValue
                      )}
                    </div>
                  </div>

                  <div
                    style={{
                      display: 'flex',
                      gap: '6px'
                    }}
                  >
                    <button
                      type="button"
                      onClick={() =>
                        openActionModal(
                          item,
                          'add'
                        )
                      }
                      disabled={loading}
                      style={{
                        width: '36px',
                        height: '36px',
                        border:
                          '1px solid #9FCBE3',
                        borderRadius:
                          '6px',
                        background:
                          '#E7F3FB',
                        color:
                          colors.darkBlue,
                        fontFamily:
                          'inherit',
                        fontSize:
                          '17px',
                        fontWeight:
                          650,
                        cursor:
                          loading
                            ? 'not-allowed'
                            : 'pointer'
                      }}
                      title="Add stock"
                    >
                      +
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        openActionModal(
                          item,
                          'remove'
                        )
                      }
                      disabled={
                        loading ||
                        Number(
                          displayQuantity
                        ) <= 0
                      }
                      style={{
                        width: '36px',
                        height: '36px',
                        border:
                          '1px solid #C9DCE6',
                        borderRadius:
                          '6px',
                        background:
                          '#FFFFFF',
                        color:
                          colors.text,
                        fontFamily:
                          'inherit',
                        fontSize:
                          '17px',
                        fontWeight:
                          650,
                        cursor:
                          loading
                            ? 'not-allowed'
                            : 'pointer'
                      }}
                      title="Remove stock"
                    >
                      −
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        openActionModal(
                          item,
                          'delete'
                        )
                      }
                      disabled={loading}
                      style={{
                        width: '36px',
                        height: '36px',
                        border:
                          '1px solid #E0B7B1',
                        borderRadius:
                          '6px',
                        background:
                          '#FFF6F5',
                        color:
                          '#A4372D',
                        fontFamily:
                          'inherit',
                        fontSize:
                          '12px',
                        fontWeight:
                          700,
                        cursor:
                          loading
                            ? 'not-allowed'
                            : 'pointer'
                      }}
                      title="Remove all stock"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </section>

      {actionItem && (
        <div
          role="presentation"
          onMouseDown={(event) => {
            if (
              event.target ===
                event.currentTarget &&
              !loading
            ) {
              closeActionModal()
            }
          }}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 1100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
            background:
              'rgba(0, 42, 68, 0.38)'
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="inventory-action-title"
            onMouseDown={(event) =>
              event.stopPropagation()
            }
            style={{
              width: 'min(430px, 100%)',
              boxSizing: 'border-box',
              padding: '25px',
              background: '#FFFFFF',
              border:
                '1px solid #B8D5E5',
              borderRadius: '10px',
              boxShadow:
                '0 18px 45px rgba(0, 55, 85, 0.22)'
            }}
          >
            <h3
              id="inventory-action-title"
              style={{
                margin: 0,
                color: colors.deepBlue,
                fontSize: '19px',
                fontWeight: 750
              }}
            >
              {actionType === 'add'
                ? 'Add Stock'
                : actionType === 'remove'
                  ? 'Remove Stock'
                  : 'Remove All Stock'}
            </h3>

            <p
              style={{
                margin: '8px 0 20px',
                color: colors.muted,
                fontSize: '13px',
                lineHeight: 1.5
              }}
            >
              {actionType === 'delete'
                ? `This will remove all ${actionItem.quantity} units of ${actionItem.name}.`
                : `Update the stock quantity for ${actionItem.name}.`}
            </p>

            {actionType !== 'delete' && (
              <>
                <label
                  htmlFor="inventory-action-quantity"
                  style={{
                    display: 'block',
                    marginBottom: '7px',
                    color: colors.text,
                    fontSize: '12px',
                    fontWeight: 650
                  }}
                >
                  Quantity
                </label>

                <input
                  id="inventory-action-quantity"
                  type="number"
                  min="1"
                  max={
                    actionType ===
                    'remove'
                      ? actionItem.quantity
                      : undefined
                  }
                  value={quantity}
                  onChange={(event) =>
                    setQuantity(
                      event.target.value
                    )
                  }
                  onKeyDown={(event) => {
                    if (
                      event.key === 'Enter' &&
                      !loading
                    ) {
                      executeAction()
                    }
                  }}
                  disabled={loading}
                  autoFocus
                  style={{
                    width: '100%',
                    height: '42px',
                    boxSizing:
                      'border-box',
                    padding:
                      '0 13px',
                    border:
                      '1px solid #C2D9E6',
                    borderRadius:
                      '7px',
                    background:
                      '#FFFFFF',
                    color:
                      colors.text,
                    fontFamily:
                      'inherit',
                    fontSize:
                      '13px',
                    outline:
                      'none'
                  }}
                />
              </>
            )}

            {actionType === 'delete' && (
              <div
                style={{
                  padding: '12px 14px',
                  background: '#FFF6F5',
                  border:
                    '1px solid #E6C4BF',
                  borderRadius: '7px',
                  color: '#8B3027',
                  fontSize: '12px'
                }}
              >
                Available quantity:{' '}
                {actionItem.quantity}{' '}
                {actionItem.unit ||
                  'units'}
              </div>
            )}

            <div
              style={{
                display: 'flex',
                justifyContent:
                  'flex-end',
                gap: '9px',
                marginTop: '20px'
              }}
            >
              <button
                type="button"
                onClick={
                  closeActionModal
                }
                disabled={loading}
                style={{
                  height: '40px',
                  padding:
                    '0 15px',
                  border:
                    '1px solid #C2D9E6',
                  borderRadius:
                    '7px',
                  background:
                    '#E7F3FB',
                  color:
                    colors.deepBlue,
                  fontFamily:
                    'inherit',
                  fontSize:
                    '12px',
                  fontWeight:
                    650,
                  cursor:
                    'pointer'
                }}
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={executeAction}
                disabled={loading}
                style={{
                  height: '40px',
                  padding:
                    '0 17px',
                  border:
                    actionType ===
                    'delete'
                      ? '1px solid #A4372D'
                      : '1px solid #005A9E',
                  borderRadius:
                    '7px',
                  background:
                    actionType ===
                    'delete'
                      ? '#A4372D'
                      : '#005A9E',
                  color:
                    '#FFFFFF',
                  fontFamily:
                    'inherit',
                  fontSize:
                    '12px',
                  fontWeight:
                    650,
                  cursor:
                    loading
                      ? 'not-allowed'
                      : 'pointer',
                  opacity:
                    loading
                      ? 0.6
                      : 1
                }}
              >
                {loading
                  ? 'Updating'
                  : actionType ===
                      'add'
                    ? 'Add Stock'
                    : actionType ===
                        'remove'
                      ? 'Remove Stock'
                      : 'Remove All'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}