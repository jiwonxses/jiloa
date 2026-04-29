import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import MovieDetail from './pages/MovieDetail'
import { isAuthenticated, getMe, clearToken } from './api'

export default function App() {
  const [dark, setDark] = useState(false)
  const [user, setUser] = useState(null)
  const [authChecked, setAuthChecked] = useState(false)

  // Au démarrage, si on a un token, on récupère le user via /auth/me
  useEffect(() => {
    if (!isAuthenticated()) {
      setAuthChecked(true)
      return
    }
    getMe()
      .then(setUser)
      .catch(() => clearToken())  // token invalide, on le supprime
      .finally(() => setAuthChecked(true))
  }, [])

  if (!authChecked) {
    return <div className="app"><p style={{ padding: '2rem' }}>Chargement...</p></div>
  }

  return (
    <div className={dark ? 'app dark' : 'app'}>
      <BrowserRouter>
        <Routes>
          <Route
            path="/"
            element={<Home dark={dark} setDark={setDark} user={user} setUser={setUser} />}
          />
          <Route
            path="/movie/:id"
            element={<MovieDetail dark={dark} setDark={setDark} user={user} setUser={setUser} />}
          />
        </Routes>
      </BrowserRouter>
    </div>
  )
}