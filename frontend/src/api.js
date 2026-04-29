const BASE = process.env.REACT_APP_API_URL ||'http://localhost:8000'

const TOKEN_KEY = 'auth_token'

// === Helpers d'authentification ===
export const getPopular = (limit = 20) => get(`/movies/popular?limit=${limit}`)
export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)
export const isAuthenticated = () => !!getToken()

// === Helpers de requêtes ===
const buildHeaders = (extra = {}) => {
  const headers = { 'Content-Type': 'application/json', ...extra }
  const token = getToken()
  if (token) headers['X-Token'] = token
  return headers
}

const handleResponse = async (response) => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    return Promise.reject(error)
  }
  // 204 No Content (delete) n'a pas de body
  if (response.status === 204) return null
  return response.json()
}

const get = (url) =>
  fetch(BASE + url, { headers: buildHeaders() }).then(handleResponse)

const post = (url, body) =>
  fetch(BASE + url, {
    method: 'POST',
    headers: buildHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  }).then(handleResponse)

const del = (url) =>
  fetch(BASE + url, {
    method: 'DELETE',
    headers: buildHeaders(),
  }).then(handleResponse)


// === Auth ===
export const register = (username, password) =>
  post('/auth/register', { username, password })

export const login = async (username, password) => {
  const data = await post('/auth/login', { username, password })
  setToken(data.token)
  return data
}

export const logout = () => clearToken()

export const getMe = () => get('/auth/me')


// === Movies ===
export const getMovie = (id) => get(`/movies/${id}`)
export const getSimilar = (id, limit = 5) => get(`/movies/${id}/similar?limit=${limit}`)

// Recherche lexicale par titre (typo-tolerant)
export const searchByTitle = (q, limit = 10) =>
  get(`/movies/search?q=${encodeURIComponent(q)}&limit=${limit}`)

// Suggestions pour autocomplete (réutilise search avec limite plus petite)
export const getSuggestions = (q) =>
  get(`/movies/search?q=${encodeURIComponent(q)}&limit=8`)

// Recherche sémantique avec 3 variantes (pure / popularity / rating)
export const searchBySynopsis = (q, limit = 10) =>
  get(`/movies/search/multi?q=${encodeURIComponent(q)}&limit=${limit}`)


// === Favorites ===
export const getFavorites = () => get('/favorites')

export const addFavorite = (movieId) => post(`/favorites/${movieId}`)

export const removeFavorite = (movieId) => del(`/favorites/${movieId}`)


// === Recommendations ===
export const getRecommendations = (limit = 10) =>
  get(`/favorites/recommendations?limit=${limit}`)