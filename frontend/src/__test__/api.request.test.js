import {
  login,
  register,
  getFavorites,
  addFavorite,
  removeFavorite,
  getMovie,
  setToken,
  getToken,
} from '../api'

describe('API requests', () => {
  beforeEach(() => {
    localStorage.clear()
    // Mock global fetch (jest.fn() au lieu de vi.fn())
    global.fetch = jest.fn()
  })

  describe('login', () => {
    it('stocke le token reçu après un login réussi', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ token: 'new-token-123', username: 'alice' }),
      })

      await login('alice', 'pwd123')

      expect(getToken()).toBe('new-token-123')
    })

    it('rejette la promise si les credentials sont mauvais', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ detail: 'Identifiants invalides' }),
      })

      await expect(login('alice', 'wrong')).rejects.toEqual({
        detail: 'Identifiants invalides',
      })
      expect(getToken()).toBeNull()
    })
  })

  describe('register', () => {
    it('appelle /auth/register avec username et password', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({ id: 1, username: 'bob' }),
      })

      const result = await register('bob', 'pwd456')

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/register'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ username: 'bob', password: 'pwd456' }),
        }),
      )
      expect(result).toEqual({ id: 1, username: 'bob' })
    })
  })

  describe('addFavorite / removeFavorite', () => {
    it('addFavorite envoie POST /favorites/{id} avec le token', async () => {
      setToken('my-token')
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({ message: 'Favorite added' }),
      })

      await addFavorite(27205)

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/favorites/27205'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({ 'X-Token': 'my-token' }),
        }),
      )
    })

    it('removeFavorite envoie DELETE /favorites/{id}', async () => {
      setToken('my-token')
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      })

      const result = await removeFavorite(27205)

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/favorites/27205'),
        expect.objectContaining({ method: 'DELETE' }),
      )
      expect(result).toBeNull()
    })
  })

  describe('getMovie', () => {
    it('appelle /movies/{id} et retourne le film', async () => {
      const fakeMovie = { id: 1, title: 'Inception' }
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => fakeMovie,
      })

      const result = await getMovie(1)

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/movies/1'),
        expect.any(Object),
      )
      expect(result).toEqual(fakeMovie)
    })
  })

  describe('getFavorites quand non authentifié', () => {
    it('appelle /favorites sans header X-Token', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => [],
      })

      await getFavorites()

      const call = global.fetch.mock.calls[0]
      const headers = call[1].headers
      expect(headers).not.toHaveProperty('X-Token')
    })
  })
})