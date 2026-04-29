import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login, register, getMe, logout, getSuggestions } from '../api'

export default function Header({ dark, setDark, user, setUser }) {
  const navigate = useNavigate()
  const [titleInput, setTitleInput] = useState('')
  const [synopsisInput, setSynopsisInput] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [showAuth, setShowAuth] = useState(false)
  const [authMode, setAuthMode] = useState('login')  // 'login' ou 'register'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef(null)
  const wrapperRef = useRef(null)

  // Fetch suggestions with debounce
  useEffect(() => {
    clearTimeout(debounceRef.current)
    if (titleInput.trim().length < 2) {
      setSuggestions([])
      return
    }
    debounceRef.current = setTimeout(() => {
      getSuggestions(titleInput.trim())
        .then(results => {
          setSuggestions(Array.isArray(results) ? results : [])
          setShowSuggestions(true)
        })
        .catch(() => setSuggestions([]))
    }, 250)
  }, [titleInput])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClick = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const handleTitleKey = (e) => {
    if (e.key === 'Enter') {
      setShowSuggestions(false)
      if (titleInput.trim()) {
        navigate(`/?title=${encodeURIComponent(titleInput.trim())}`)
      } else {
        navigate('/')
      }
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
    }
  }

  const handleSuggestionClick = (title) => {
    setTitleInput(title)
    setShowSuggestions(false)
    navigate(`/?title=${encodeURIComponent(title)}`)
  }

  const handleSynopsisKey = (e) => {
    if (e.key === 'Enter') {
      if (synopsisInput.trim()) {
        navigate(`/?synopsis=${encodeURIComponent(synopsisInput.trim())}`)
      } else {
        navigate('/')
      }
    }
  }

  const handleAuth = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (authMode === 'register') {
        await register(username, password)
        // Auto-login après création
        await login(username, password)
      } else {
        await login(username, password)
      }

      // Récupère les infos du user créé/connecté
      const userData = await getMe()
      setUser(userData)
      setShowAuth(false)
      setUsername('')
      setPassword('')
    } catch (err) {
      setError(err.detail || `Erreur de ${authMode === 'login' ? 'connexion' : 'création de compte'}`)
    } finally {
      setLoading(false)
    }
  }

  const switchAuthMode = () => {
    setAuthMode(authMode === 'login' ? 'register' : 'login')
    setError('')
  }

  const handleLogout = () => {
    logout()
    setUser(null)
  }

  return (
    <div className="header">
      <Link to="/">Jiloa</Link>

      <div className="search-wrapper" ref={wrapperRef}>
        <input
          placeholder="Titre..."
          value={titleInput}
          onChange={e => { setTitleInput(e.target.value); setShowSuggestions(true) }}
          onKeyDown={handleTitleKey}
          onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
          autoComplete="off"
        />
        {showSuggestions && suggestions.length > 0 && (
          <ul className="suggestions">
            {suggestions.map(m => (
              <li key={m.id} onMouseDown={() => handleSuggestionClick(m.title)}>
                {m.title}
              </li>
            ))}
          </ul>
        )}
      </div>

      <input
        placeholder="Synopsis..."
        value={synopsisInput}
        onChange={e => setSynopsisInput(e.target.value)}
        onKeyDown={handleSynopsisKey}
      />

      <button onClick={() => setDark(!dark)}>{dark ? 'Clair' : 'Sombre'}</button>

      {user ? (
        <>
          <span>{user.username}</span>
          <button onClick={handleLogout}>Déconnexion</button>
        </>
      ) : (
        <button onClick={() => { setShowAuth(!showAuth); setError('') }}>
          Connexion
        </button>
      )}

      {showAuth && !user && (
        <div className="login-form">
          <form
            onSubmit={handleAuth}
            style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}
          >
            <input
              placeholder="Nom d'utilisateur"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              minLength={3}
            />
            <input
              placeholder="Mot de passe"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={4}
            />
            <button type="submit" disabled={loading}>
              {loading
                ? '...'
                : authMode === 'login'
                  ? 'Se connecter'
                  : 'Créer le compte'}
            </button>
            <button
              type="button"
              className="link-button"
              onClick={switchAuthMode}
            >
              {authMode === 'login'
                ? 'Pas de compte ? Créer un compte'
                : 'Déjà un compte ? Se connecter'}
            </button>
          </form>
          {error && <p className="login-error">{error}</p>}
        </div>
      )}
    </div>
  )
}