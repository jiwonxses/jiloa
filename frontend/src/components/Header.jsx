import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login, getSuggestions } from '../api'

export default function Header({ dark, setDark, user, setUser }) {
  const navigate = useNavigate()
  const [titleInput, setTitleInput] = useState('')
  const [synopsisInput, setSynopsisInput] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [showLogin, setShowLogin] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
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
    const result = await login(username, password)
    if (result.detail) {
      setError(result.detail)
      return
    }
    setUser(result)
    setShowLogin(false)
    setUsername('')
    setPassword('')
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
          <button onClick={() => setUser(null)}>Déconnexion</button>
        </>
      ) : (
        <button onClick={() => { setShowLogin(!showLogin); setError('') }}>Connexion</button>
      )}

      {showLogin && !user && (
        <div className="login-form">
          <form onSubmit={handleAuth} style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <input
              placeholder="Nom d'utilisateur"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
            />
            <input
              placeholder="Mot de passe"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
            <button type="submit">Se connecter</button>
          </form>
          {error && <p className="login-error">{error}</p>}
        </div>
      )}
    </div>
  )
}
