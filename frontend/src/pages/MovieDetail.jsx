import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import MovieRow from '../components/MovieRow'
import { getMovie, getSimilar, getFavorites, addFavorite, removeFavorite } from '../api'

const PLACEHOLDER = 'https://placehold.co/200x300?text=No+Image'

export default function MovieDetail({ dark, setDark, user, setUser }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const [movie, setMovie] = useState(null)
  const [similar, setSimilar] = useState([])
  const [favorites, setFavorites] = useState([])
  const [isFavorite, setIsFavorite] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([getMovie(id), getSimilar(id)])
      .then(([m, s]) => {
        setMovie(m)
        setSimilar(s)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  const loadFavorites = () => {
  if (user) {
    getFavorites().then(favs => {           // ← plus de user.id
      setFavorites(favs)
      setIsFavorite(favs.some(f => f.id === parseInt(id)))
    })
  }
}

const toggleFavorite = async () => {
  if (!user) return
  try {
    if (isFavorite) await removeFavorite(id)    // ← juste l'id du film
    else await addFavorite(id)                   // ← juste l'id du film
    loadFavorites()
  } catch (err) {
    console.error('Erreur favori:', err)
    alert(err.detail || 'Erreur lors de la modification du favori')
  }
}

  if (loading) {
    return (
      <>
        <Header dark={dark} setDark={setDark} user={user} setUser={setUser} />
        <div className="detail"><p>Chargement...</p></div>
      </>
    )
  }

  if (!movie || movie.detail) {
    return (
      <>
        <Header dark={dark} setDark={setDark} user={user} setUser={setUser} />
        <div className="detail"><p>Film non trouvé.</p></div>
      </>
    )
  }

  return (
    <>
      <Header dark={dark} setDark={setDark} user={user} setUser={setUser} />
      <div className="detail">
        <button onClick={() => navigate(-1)}>← Retour</button>

        <div className="detail-top">
          <img
            src={movie.poster || PLACEHOLDER}
            alt={movie.title}
            onError={e => { e.target.src = PLACEHOLDER }}
          />
          <div className="detail-info">
            <h1>{movie.title}</h1>
            <p>{movie.date_publication?.substring(0, 4)}</p>
            <p>{movie.vote_average ? Number(movie.vote_average).toFixed(1) : 'N/A'} / 10</p>
            {movie.genres?.length > 0 && (
              <p className="genres">{movie.genres.join(', ')}</p>
            )}
            <p className="overview">{movie.overview}</p>
            {user && (
              <button className="fav-toggle" onClick={toggleFavorite}>
                {isFavorite ? '♥ Retirer des favoris' : '♡ Ajouter aux favoris'}
              </button>
            )}
          </div>
        </div>

        <MovieRow
          title="Films similaires"
          movies={similar}
          loading={false}
          user={user}
          favorites={favorites}
          onFavoriteChange={loadFavorites}
        />
      </div>
    </>
  )
}
