import {
  useState,
  useEffect,
  useCallback,
  useMemo
} from 'react'

const API_BASE =
  import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Dashboard({
  stats,
  inventory,
  onRefresh,
  onFeedback
}) {
  const [transactions, setTransactions] =
    useState([])

  const [categories, setCategories] =
    useState([])

  const [selectedCategory, setSelectedCategory] =
    useState('all')

  const [searchTerm, setSearchTerm] =
    useState('')

  const [loading, setLoading] =
    useState(false)

  const [restockingItem, setRestockingItem] =
    useState(null)

  const [restockQuantity, setRestockQuantity] =
    useState('10')

  const [lowStockItems, setLowStockItems] =
    useState([])

  const fetchTransactions =
    useCallback(async () => {
      try {
        const response = await fetch(
          `${API_BASE}/api/inventory/transactions?limit=15`
        )

        if (!response.ok) {
          throw new Error(
            'Unable to load transactions'
          )
        }

        const data = await response.json()

        setTransactions(
          Array.isArray(data) ? data : []
        )
      } catch (error) {
        console.error(
          'Failed to fetch transactions:',
          error
        )

        setTransactions([])
      }
    }, [])

  const fetchCategories =
    useCallback(async () => {
      try {
        const response = await fetch(
          `${API_BASE}/api/inventory/categories`
        )

        if (!response.ok) {
          throw new Error(
            'Unable to load categories'
          )
        }

        const data = await response.json()

        setCategories(
          Array.isArray(data) ? data : []
        )
      } catch (error) {
        console.error(
          'Failed to fetch categories:',
          error
        )

        setCategories([])
      }
    }, [])

  const fetchLowStock =
    useCallback(async () => {
      try {
        const response = await fetch(
          `${API_BASE}/api/inventory/low-stock`
        )

        if (!response.ok) {
          throw new Error(
            'Unable to load low stock items'
          )
        }

        const data = await response.json()

        setLowStockItems(
          Array.isArray(data) ? data : []
        )
      } catch (error) {
        console.error(
          'Failed to fetch low stock items:',
          error
        )

        setLowStockItems([])
      }
    }, [])

  useEffect(() => {
    fetchTransactions()
    fetchCategories()
    fetchLowStock()
  }, [
    fetchTransactions,
    fetchCategories,
    fetchLowStock
  ])

  const openRestockModal = useCallback(
    (itemName) => {
      setRestockQuantity('10')
      setRestockingItem(itemName)
    },
    []
  )

  const closeRestockModal = useCallback(() => {
    if (!loading) {
      setRestockingItem(null)
      setRestockQuantity('10')
    }
  }, [loading])

  const handleRestock =
    useCallback(async () => {
      if (!restockingItem) {
        return
      }

      const quantity = Number.parseInt(
        restockQuantity,
        10
      )

      if (
        !Number.isInteger(quantity) ||
        quantity <= 0
      ) {
        onFeedback(
          'Please enter a valid positive quantity.'
        )
        return
      }

      setLoading(true)

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
              name: restockingItem,
              quantity
            })
          }
        )

        if (!response.ok) {
          throw new Error(
            'Restock request failed'
          )
        }

        onFeedback(
          `Restocked ${quantity} units of ${restockingItem}.`
        )

        setRestockingItem(null)
        setRestockQuantity('10')

        await Promise.all([
          onRefresh(),
          fetchLowStock(),
          fetchTransactions()
        ])
      } catch (error) {
        console.error(
          'Failed to restock item:',
          error
        )

        onFeedback(
          'Unable to restock the selected item.'
        )
      } finally {
        setLoading(false)
      }
    }, [
      restockingItem,
      restockQuantity,
      onFeedback,
      onRefresh,
      fetchLowStock,
      fetchTransactions
    ])

  const filteredInventory = useMemo(() => {
    if (!Array.isArray(inventory)) {
      return []
    }

    const normalizedSearch =
      searchTerm.trim().toLowerCase()

    return inventory.filter((item) => {
      const matchesCategory =
        selectedCategory === 'all' ||
        item.category === selectedCategory

      const matchesSearch =
        !normalizedSearch ||
        String(item.name || '')
          .toLowerCase()
          .includes(normalizedSearch)

      return (
        matchesCategory &&
        matchesSearch
      )
    })
  }, [
    inventory,
    selectedCategory,
    searchTerm
  ])

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

  const statsData = useMemo(() => {
    const calculatedQuantity =
      Array.isArray(inventory)
        ? inventory.reduce(
            (sum, item) =>
              sum +
              Number(item.quantity || 0),
            0
          )
        : 0

    return {
      totalItems:
        stats?.total_items ??
        (Array.isArray(inventory)
          ? inventory.length
          : 0),

      totalQuantity:
        stats?.total_quantity ??
        calculatedQuantity,

      totalValue:
        stats?.total_value ??
        totalValue,

      lowStockItems:
        stats?.low_stock_items ??
        lowStockItems.length
    }
  }, [
    stats,
    inventory,
    totalValue,
    lowStockItems.length
  ])

  const clearFilters = useCallback(() => {
    setSearchTerm('')
    setSelectedCategory('all')
    onFeedback('Filters cleared.')
  }, [onFeedback])

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

  const formatTime = (timestamp) => {
    if (!timestamp) {
      return 'Unavailable'
    }

    try {
      const date = new Date(timestamp)

      return (
        date.toLocaleDateString(
          'en-IN',
          {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
          }
        ) +
        ' ' +
        date.toLocaleTimeString(
          'en-IN',
          {
            hour: '2-digit',
            minute: '2-digit'
          }
        )
      )
    } catch {
      return 'Unavailable'
    }
  }

  const hasActiveFilters =
    searchTerm.trim() !== '' ||
    selectedCategory !== 'all'

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

  const sectionStyle = {
    background: '#FFFFFF',
    border: `1px solid ${colors.border}`,
    borderRadius: '10px',
    marginBottom: '20px',
    overflow: 'hidden'
  }

  const sectionHeaderStyle = {
    padding: '19px 22px',
    borderBottom: '1px solid #DCEAF2'
  }

  const fieldStyle = {
    width: '100%',
    height: '42px',
    boxSizing: 'border-box',
    padding: '0 13px',
    border: '1px solid #C2D9E6',
    borderRadius: '7px',
    background: '#FFFFFF',
    color: colors.text,
    fontFamily: 'inherit',
    fontSize: '13px',
    outline: 'none'
  }

  const primaryButtonStyle = {
    height: '38px',
    padding: '0 15px',
    border: '1px solid #005A9E',
    borderRadius: '7px',
    background: '#005A9E',
    color: '#FFFFFF',
    fontFamily: 'inherit',
    fontSize: '12px',
    fontWeight: 600,
    cursor: loading
      ? 'not-allowed'
      : 'pointer',
    opacity: loading ? 0.6 : 1,
    whiteSpace: 'nowrap'
  }

  const secondaryButtonStyle = {
    height: '40px',
    padding: '0 15px',
    border: '1px solid #C2D9E6',
    borderRadius: '7px',
    background: '#E7F3FB',
    color: colors.deepBlue,
    fontFamily: 'inherit',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer'
  }

  return (
    <div
      style={{
        width: '100%',
        color: colors.text,
        fontFamily:
          'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
      }}
    >
      <div
        style={{
          marginBottom: '24px'
        }}
      >
        <h2
          style={{
            margin: 0,
            color: colors.deepBlue,
            fontSize: '28px',
            lineHeight: 1.2,
            fontWeight: 750,
            letterSpacing: '-0.4px'
          }}
        >
          Inventory Dashboard
        </h2>

        <p
          style={{
            margin: '8px 0 0',
            color: colors.muted,
            fontSize: '14px'
          }}
        >
          Monitor inventory levels, stock value and recent activity.
        </p>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns:
            'repeat(auto-fit, minmax(190px, 1fr))',
          gap: '14px',
          marginBottom: '24px'
        }}
      >
        {[
          {
            label: 'Total Items',
            value: statsData.totalItems,
            detail: 'Distinct inventory items'
          },
          {
            label: 'Total Units',
            value: statsData.totalQuantity,
            detail: 'Current quantity in stock'
          },
          {
            label: 'Low Stock',
            value: statsData.lowStockItems,
            detail: 'Items requiring attention'
          },
          {
            label: 'Inventory Value',
            value: formatCurrency(
              statsData.totalValue
            ),
            detail: 'Current estimated value'
          }
        ].map((stat) => (
          <div
            key={stat.label}
            style={{
              background: '#FFFFFF',
              border: `1px solid ${colors.border}`,
              borderRadius: '10px',
              padding: '19px',
              minHeight: '118px',
              boxSizing: 'border-box',
              borderTop:
                '3px solid #0078D4'
            }}
          >
            <div
              style={{
                color: colors.muted,
                fontSize: '12px',
                fontWeight: 650,
                marginBottom: '14px'
              }}
            >
              {stat.label}
            </div>

            <div
              style={{
                color: colors.deepBlue,
                fontSize: '25px',
                fontWeight: 750,
                overflowWrap: 'anywhere'
              }}
            >
              {stat.value}
            </div>

            <div
              style={{
                marginTop: '8px',
                color: '#7890A0',
                fontSize: '11px'
              }}
            >
              {stat.detail}
            </div>
          </div>
        ))}
      </div>

      {lowStockItems.length > 0 && (
        <section style={sectionStyle}>
          <div style={sectionHeaderStyle}>
            <h3
              style={{
                margin: 0,
                color: colors.deepBlue,
                fontSize: '17px',
                fontWeight: 700
              }}
            >
              Stock Attention
            </h3>

            <p
              style={{
                margin: '6px 0 0',
                color: colors.muted,
                fontSize: '12px'
              }}
            >
              These items have reached the low-stock threshold.
            </p>
          </div>

          {lowStockItems.map((item) => (
            <div
              key={item.id || item.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '16px',
                padding: '15px 22px',
                borderBottom:
                  '1px solid #DCEAF2'
              }}
            >
              <div>
                <div
                  style={{
                    color: colors.text,
                    fontSize: '14px',
                    fontWeight: 650
                  }}
                >
                  {item.name}
                </div>

                <div
                  style={{
                    marginTop: '5px',
                    color: colors.muted,
                    fontSize: '12px'
                  }}
                >
                  Current quantity:{' '}
                  {item.quantity}{' '}
                  {item.unit || 'units'}
                </div>
              </div>

              <button
                type="button"
                onClick={() =>
                  openRestockModal(item.name)
                }
                disabled={loading}
                style={primaryButtonStyle}
              >
                Restock
              </button>
            </div>
          ))}
        </section>
      )}

      <section style={sectionStyle}>
        <div style={sectionHeaderStyle}>
          <h3
            style={{
              margin: 0,
              color: colors.deepBlue,
              fontSize: '17px',
              fontWeight: 700
            }}
          >
            Inventory Overview
          </h3>

          <p
            style={{
              margin: '6px 0 0',
              color: colors.muted,
              fontSize: '12px'
            }}
          >
            Search and filter the current inventory.
          </p>
        </div>

        <div
          style={{
            padding: '18px 22px'
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns:
                'minmax(0, 1fr) 220px auto',
              gap: '10px'
            }}
          >
            <input
              type="text"
              placeholder="Search inventory"
              value={searchTerm}
              onChange={(event) =>
                setSearchTerm(
                  event.target.value
                )
              }
              style={fieldStyle}
            />

            <select
              value={selectedCategory}
              onChange={(event) =>
                setSelectedCategory(
                  event.target.value
                )
              }
              style={fieldStyle}
            >
              <option value="all">
                All Categories
              </option>

              {categories.map((category) => (
                <option
                  key={category}
                  value={category}
                >
                  {category}
                </option>
              ))}
            </select>

            {hasActiveFilters ? (
              <button
                type="button"
                onClick={clearFilters}
                style={secondaryButtonStyle}
              >
                Clear
              </button>
            ) : (
              <div />
            )}
          </div>
        </div>

        <div
          style={{
            padding: '0 22px 20px'
          }}
        >
          {filteredInventory.length === 0 ? (
            <div
              style={{
                padding: '28px 0',
                textAlign: 'center',
                color: colors.muted,
                fontSize: '13px'
              }}
            >
              No inventory items match the current filters.
            </div>
          ) : (
            filteredInventory
              .slice(0, 5)
              .map((item) => (
                <div
                  key={item.id || item.name}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '16px',
                    padding: '14px 0',
                    borderBottom:
                      '1px solid #DCEAF2'
                  }}
                >
                  <div>
                    <div
                      style={{
                        color: colors.text,
                        fontSize: '13px',
                        fontWeight: 650
                      }}
                    >
                      {item.name}
                    </div>

                    <div
                      style={{
                        marginTop: '4px',
                        color: colors.muted,
                        fontSize: '11px'
                      }}
                    >
                      {item.category ||
                        'Uncategorized'}
                    </div>
                  </div>

                  <div
                    style={{
                      color: colors.darkBlue,
                      fontSize: '12px',
                      fontWeight: 650,
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {item.quantity}{' '}
                    {item.unit || 'units'}
                  </div>
                </div>
              ))
          )}
        </div>
      </section>

      <section style={sectionStyle}>
        <div style={sectionHeaderStyle}>
          <h3
            style={{
              margin: 0,
              color: colors.deepBlue,
              fontSize: '17px',
              fontWeight: 700
            }}
          >
            Recent Transactions
          </h3>

          <p
            style={{
              margin: '6px 0 0',
              color: colors.muted,
              fontSize: '12px'
            }}
          >
            Recent inventory additions and removals.
          </p>
        </div>

        {transactions.length === 0 ? (
          <div
            style={{
              padding: '28px 22px',
              textAlign: 'center',
              color: colors.muted,
              fontSize: '13px'
            }}
          >
            No inventory transactions are available.
          </div>
        ) : (
          <div
            style={{
              overflowX: 'auto'
            }}
          >
            <div
              style={{
                minWidth: '720px'
              }}
            >
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns:
                    'minmax(130px, 1fr) 100px 90px 120px 145px',
                  gap: '14px',
                  padding: '11px 22px',
                  background: '#E7F3FB',
                  borderBottom:
                    '1px solid #D0E3EE',
                  color: '#557387',
                  fontSize: '10px',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}
              >
                <span>Item</span>
                <span>Action</span>
                <span>Quantity</span>
                <span>Value</span>
                <span>Date</span>
              </div>

              {transactions
                .slice(0, 10)
                .map((transaction) => (
                  <div
                    key={transaction.id}
                    style={{
                      display: 'grid',
                      gridTemplateColumns:
                        'minmax(130px, 1fr) 100px 90px 120px 145px',
                      alignItems: 'center',
                      gap: '14px',
                      padding: '14px 22px',
                      borderBottom:
                        '1px solid #DCEAF2',
                      fontSize: '12px'
                    }}
                  >
                    <span
                      style={{
                        color: colors.text,
                        fontWeight: 650
                      }}
                    >
                      {transaction.item_name}
                    </span>

                    <span
                      style={{
                        color:
                          transaction.action ===
                          'add'
                            ? '#16803C'
                            : '#B42318',
                        fontSize: '11px',
                        fontWeight: 700,
                        textTransform:
                          'uppercase'
                      }}
                    >
                      {transaction.action ===
                      'add'
                        ? 'Added'
                        : 'Removed'}
                    </span>

                    <span
                      style={{
                        color: colors.muted
                      }}
                    >
                      {transaction.quantity} units
                    </span>

                    <span
                      style={{
                        color: colors.deepBlue,
                        fontWeight: 650
                      }}
                    >
                      {transaction.total_value >
                      0
                        ? formatCurrency(
                            transaction.total_value
                          )
                        : transaction.price >
                            0
                          ? formatCurrency(
                              transaction.price
                            )
                          : '—'}
                    </span>

                    <span
                      style={{
                        color: colors.muted
                      }}
                    >
                      {formatTime(
                        transaction.timestamp
                      )}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </section>

      {restockingItem && (
        <div
          role="presentation"
          onMouseDown={(event) => {
            if (
              event.target ===
                event.currentTarget &&
              !loading
            ) {
              closeRestockModal()
            }
          }}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 1000,
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
            aria-labelledby="restock-title"
            onMouseDown={(event) =>
              event.stopPropagation()
            }
            style={{
              width: 'min(420px, 100%)',
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
              id="restock-title"
              style={{
                margin: 0,
                color: colors.deepBlue,
                fontSize: '19px',
                fontWeight: 750
              }}
            >
              Restock Item
            </h3>

            <p
              style={{
                margin: '8px 0 20px',
                color: colors.muted,
                fontSize: '13px'
              }}
            >
              Add stock for{' '}
              <strong>
                {restockingItem}
              </strong>
              .
            </p>

            <label
              htmlFor="restock-quantity"
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
              id="restock-quantity"
              type="number"
              min="1"
              value={restockQuantity}
              onChange={(event) =>
                setRestockQuantity(
                  event.target.value
                )
              }
              onKeyDown={(event) => {
                if (
                  event.key === 'Enter' &&
                  !loading
                ) {
                  handleRestock()
                }
              }}
              style={fieldStyle}
              disabled={loading}
              autoFocus
            />

            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: '9px',
                marginTop: '20px'
              }}
            >
              <button
                type="button"
                onClick={closeRestockModal}
                disabled={loading}
                style={secondaryButtonStyle}
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={handleRestock}
                disabled={loading}
                style={{
                  ...primaryButtonStyle,
                  height: '40px'
                }}
              >
                {loading
                  ? 'Updating'
                  : 'Add Stock'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}