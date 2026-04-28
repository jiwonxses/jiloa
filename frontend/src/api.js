const BASE = 'http://localhost:8000'

const get = (url) =>
  fetch(BASE + url).then(r => {
    if (!r.ok) return r.json().then(e => Promise.reject(e))
    return r.json()
  })

const post = (url, body) =>
  fetch(BASE + url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(r => r.json())

export const getPopular = () => get('/movies/popular')
export const getRecommended = () => get('/movies/recommended')
export const searchByTitle = (q) => get(`/movies/search?title=${encodeURIComponent(q)}`)
export const getSuggestions = (q) => get(`/movies/search?title=${encodeURIComponent(q)}&limit=8`)
export const searchBySynopsis = (q) => get(`/movies/search/synopsis?q=${encodeURIComponent(q)}`)
export const getMovie = (id) => get(`/movies/${id}`)
export const getSimilar = (id) => get(`/movies/${id}/similar`)

export const login = (username, password) => post('/auth/login', { username, password })
export const register = (username, password) => post('/auth/register', { username, password })

export const getFavorites = (userId) => get(`/users/me/favorites?user_id=${userId}`)

export const addFavorite = (userId, movieId) =>
  fetch(`${BASE}/users/me/favorites/${movieId}?user_id=${userId}`, { method: 'POST' }).then(r => r.json())

export const removeFavorite = (userId, movieId) =>
  fetch(`${BASE}/users/me/favorites/${movieId}?user_id=${userId}`, { method: 'DELETE' }).then(r => r.json())
