import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import Header from '../components/Header'
import MovieRow from '../components/MovieRow'
import MovieCard from '../components/MovieCard'
import { getPopular, getRecommendations, getFavorites, searchByTitle, searchBySynopsis } from '../api'

export default function Home({ dark, setDark, user, setUser }) {
  const [searchParams] = useSearchParams()
  const [popular, setPopular] = useState([])
  const [recommended, setRecommended] = useState([])
  const [favorites, setFavorites] = useState([])
  const [searchResults, setSearchResults] = useState(null)
  const [synopsisResults, setSynopsisResults] = useState(null)  // ← nouveau, contient les 3 listes
  const [searchLabel, setSearchLabel] = useState('')
  const [loadingMain, setLoadingMain] = useState(true)
  const [loadingSearch, setLoadingSearch] = useState(false)

  useEffect(() => {
    setLoadingMain(true)
    getPopular()
      .then(setPopular)
      .catch(() => setPopular([]))
      .finally(() => setLoadingMain(false))
  }, [])

  useEffect(() => {
    if (!user) {
      setRecommended([])
      return
    }
    getRecommendations()
      .then(setRecommended)
      .catch(() => setRecommended([]))
  }, [user])

  const loadFavorites = useCallback(() => {
    if (!user) {
      setFavorites([])
      return
    }
    getFavorites()
      .then(setFavorites)
      .catch(() => setFavorites([]))
  }, [user])

  useEffect(() => {
    loadFavorites()
  }, [loadFavorites])

  useEffect(() => {
    const title = searchParams.get('title')
    const synopsis = searchParams.get('synopsis')

    // reset des deux modes de recherche à chaque changement
    setSearchResults(null)
    setSynopsisResults(null)

    if (title) {
      setLoadingSearch(true)
      setSearchLabel(`titre: "${title}"`)
      searchByTitle(title)
        .then(setSearchResults)
        .catch(() => setSearchResults([]))
        .finally(() => setLoadingSearch(false))
    } else if (synopsis) {
      setLoadingSearch(true)
      setSearchLabel(`synopsis: "${synopsis}"`)
      searchBySynopsis(synopsis)
        .then(setSynopsisResults)  // on stocke l'objet entier { pure, by_popularity, by_rating }
        .catch(() => setSynopsisResults({ pure: [], by_popularity: [], by_rating: [] }))
        .finally(() => setLoadingSearch(false))
    } else {
      setSearchLabel('')
    }
  }, [searchParams])

  // recherche sémantique avec 3 listes
  if (synopsisResults !== null) {
    return (
      <>
        <Header dark={dark} setDark={setDark} user={user} setUser={setUser} />
        <div className="section">
          <h2>Résultats pour {searchLabel}</h2>
          {loadingSearch ? (
            <p>Chargement...</p>
          ) : (
            <>
              <MovieRow
                title="Plus pertinents"
                movies={synopsisResults.pure}
                loading={false}
                user={user}
                favorites={favorites}
                onFavoriteChange={loadFavorites}
              />
              <MovieRow
                title="Boostés popularité"
                movies={synopsisResults.by_popularity}
                loading={false}
                user={user}
                favorites={favorites}
                onFavoriteChange={loadFavorites}
              />
              <MovieRow
                title="Boostés notes"
                movies={synopsisResults.by_rating}
                loading={false}
                user={user}
                favorites={favorites}
                onFavoriteChange={loadFavorites}
              />
            </>
          )}
        </div>
      </>
    )
  }

  // recherche par titre (liste simple)
  if (searchResults !== null) {
    return (
      <>
        <Header dark={dark} setDark={setDark} user={user} setUser={setUser} />
        <div className="section">
          <h2>Résultats pour {searchLabel} ({searchResults.length})</h2>
          {loadingSearch ? (
            <p>Chargement...</p>
          ) : (
            <div className="movie-row" style={{ flexWrap: 'wrap' }}>
              {searchResults.map(m => (
                <MovieCard
                  key={m.id}
                  movie={m}
                  user={user}
                  isFavorite={favorites.some(f => String(f.id) === String(m.id))}
                  onFavoriteChange={loadFavorites}
                />
              ))}
              {searchResults.length === 0 && <p>Aucun résultat.</p>}
            </div>
          )}
        </div>
      </>
    )
  }

  // page d'accueil normale
  return (
    <>
      <Header dark={dark} setDark={setDark} user={user} setUser={setUser} />
      {user && recommended.length > 0 && (
        <MovieRow
          title="Films recommandés pour vous"
          movies={recommended}
          loading={loadingMain}
          user={user}
          favorites={favorites}
          onFavoriteChange={loadFavorites}
        />
      )}
      <MovieRow
        title="Films populaires"
        movies={popular}
        loading={loadingMain}
        user={user}
        favorites={favorites}
        onFavoriteChange={loadFavorites}
      />
      {user && favorites.length > 0 && (
        <MovieRow
          title="Mes favoris"
          movies={favorites}
          loading={false}
          user={user}
          favorites={favorites}
          onFavoriteChange={loadFavorites}
        />
      )}
    </>
  )
}