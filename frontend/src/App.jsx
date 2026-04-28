import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import MovieDetail from './pages/MovieDetail'

export default function App() {
  const [dark, setDark] = useState(false)
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user')
    return saved ? JSON.parse(saved) : null
  })

  const handleSetUser = (u) => {
    setUser(u)
    if (u) localStorage.setItem('user', JSON.stringify(u))
    else localStorage.removeItem('user')
  }

  return (
    <div className={dark ? 'app dark' : 'app'}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home dark={dark} setDark={setDark} user={user} setUser={handleSetUser} />} />
          <Route path="/movie/:id" element={<MovieDetail dark={dark} setDark={setDark} user={user} setUser={handleSetUser} />} />
        </Routes>
      </BrowserRouter>
    </div>
  )
}
