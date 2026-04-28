import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import Header from '../components/Header'
import MovieRow from '../components/MovieRow'
import MovieCard from '../components/MovieCard'
import { getPopular, getRecommended, getFavorites, searchByTitle, searchBySynopsis } from '../api'

export default function Home({ dark, setDark, user, setUser }) {
  const [searchParams] = useSearchParams()
  const [popular, setPopular] = useState([])
  const [recommended, setRecommended] = useState([])
  const [favorites, setFavorites] = useState([])
  const [searchResults, setSearchResults] = useState(null)
  const [searchLabel, setSearchLabel] = useState('')
  const [loadingMain, setLoadingMain] = useState(true)
  const [loadingSearch, setLoadingSearch] = useState(false)

  useEffect(() => {
    Promise.all([getPopular(), getRecommended()])
      .then(([pop, rec]) => {
        setPopular(pop)
        setRecommended(rec)
      })
      .catch(() => {})
      .finally(() => setLoadingMain(false))
  }, [])

  const loadFavorites = useCallback(() => {
    if (user) getFavorites(user.id).then(setFavorites).catch(() => {})
    else setFavorites([])
  }, [user])

  useEffect(() => {
    loadFavorites()
  }, [loadFavorites])

  useEffect(() => {
    const title = searchParams.get('title')
    const synopsis = searchParams.get('synopsis')

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
        .then(setSearchResults)
        .catch(() => setSearchResults([]))
        .finally(() => setLoadingSearch(false))
    } else {
      setSearchResults(null)
      setSearchLabel('')
    }
  }, [searchParams])

  return (
    <>
      <Header dark={dark} setDark={setDark} user={user} setUser={setUser} />

      {searchResults !== null ? (
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
                  isFavorite={favorites.some(f => f.id === m.id)}
                  onFavoriteChange={loadFavorites}
                />
              ))}
              {searchResults.length === 0 && <p>Aucun résultat.</p>}
            </div>
          )}
        </div>
      ) : (
        <>
          <MovieRow
            title="Films recommandés"
            movies={recommended}
            loading={loadingMain}
            user={user}
            favorites={favorites}
            onFavoriteChange={loadFavorites}
          />
          <MovieRow
            title="Films populaires"
            movies={popular}
            loading={loadingMain}
            user={user}
            favorites={favorites}
            onFavoriteChange={loadFavorites}
          />
          {user && (
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
      )}
    </>
  )
}
