import MovieCard from './MovieCard'

export default function MovieRow({ title, movies, loading, user, favorites, onFavoriteChange }) {
  if (loading) {
    return (
      <div className="section">
        <h2>{title}</h2>
        <p>Chargement...</p>
      </div>
    )
  }

  if (!Array.isArray(movies) || movies.length === 0) return null

  return (
    <div className="section">
      <h2>{title}</h2>
      <div className="movie-row">
        {movies.map(m => (
          <MovieCard
            key={m.id}
            movie={m}
            user={user}
            isFavorite={favorites?.some(f => f.id === m.id) ?? false}
            onFavoriteChange={onFavoriteChange}
          />
        ))}
      </div>
    </div>
  )
}
