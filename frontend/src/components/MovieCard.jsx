import { useNavigate } from 'react-router-dom'
import { addFavorite, removeFavorite } from '../api'

const PLACEHOLDER = 'https://placehold.co/130x195?text=No+Image'

export default function MovieCard({ movie, user, isFavorite, onFavoriteChange }) {
  const navigate = useNavigate()

  const toggleFavorite = async (e) => {
    e.stopPropagation()
    if (!user) return
    if (isFavorite) {
      await removeFavorite(user.id, movie.id)
    } else {
      await addFavorite(user.id, movie.id)
    }
    onFavoriteChange?.()
  }

  return (
    <div className="movie-card" onClick={() => navigate(`/movie/${movie.id}`)}>
      <img
        src={movie.poster || PLACEHOLDER}
        alt={movie.title}
        onError={e => { e.target.src = PLACEHOLDER }}
      />
      <p className="card-title" title={movie.title}>{movie.title}</p>
      <p className="card-score">
        {movie.vote_average ? Number(movie.vote_average).toFixed(1) : 'N/A'} / 10
      </p>
      {user && (
        <button className="fav-btn" onClick={toggleFavorite}>
          {isFavorite ? '♥' : '♡'}
        </button>
      )}
    </div>
  )
}
