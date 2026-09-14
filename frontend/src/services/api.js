const API_BASE =
  import.meta.env.VITE_API_URL ||
  'http://localhost:8000'

async function request(
  endpoint,
  options = {}
) {
  const response = await fetch(
    `${API_BASE}${endpoint}`,
    options
  )

  let data = null

  try {
    data = await response.json()
  } catch {
    data = null
  }

  if (!response.ok) {
    const message =
      typeof data?.detail === 'string'
        ? data.detail
        : typeof data?.message === 'string'
          ? data.message
          : `Request failed with status ${response.status}`

    throw new Error(message)
  }

  return data
}

export async function getInventory() {
  return request('/api/inventory/')
}

export async function getInventoryStats() {
  return request('/api/inventory/stats')
}

export async function addInventoryItem(
  name,
  quantity
) {
  return request('/api/inventory/add', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      name,
      quantity
    })
  })
}

export async function removeInventoryItem(
  name,
  quantity
) {
  return request('/api/inventory/remove', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      name,
      quantity
    })
  })
}

export async function parseCommand(text) {
  return request('/api/parse/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      text
    })
  })
}

export async function detectImage(file) {
  const formData = new FormData()

  formData.append('image', file)

  return request('/api/vision/detect', {
    method: 'POST',
    body: formData
  })
}

export async function detectVideo(file) {
  const formData = new FormData()

  formData.append('video', file)

  return request('/api/vision/detect-video', {
    method: 'POST',
    body: formData
  })
}

export async function transcribeAudio(file) {
  const formData = new FormData()

  formData.append('file', file)

  return request('/api/voice/transcribe', {
    method: 'POST',
    body: formData
  })
}

export async function checkHealth() {
  return request('/health')
}

export { API_BASE }