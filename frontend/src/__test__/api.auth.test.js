import {
  getToken,
  setToken,
  clearToken,
  isAuthenticated,
} from '../api'

describe('API auth helpers', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  describe('getToken / setToken / clearToken', () => {
    it("retourne null quand aucun token n'est stocké", () => {
      expect(getToken()).toBeNull()
    })

    it('stocke et récupère un token', () => {
      setToken('abc123')
      expect(getToken()).toBe('abc123')
    })

    it('clearToken supprime le token', () => {
      setToken('abc123')
      clearToken()
      expect(getToken()).toBeNull()
    })

    it('setToken écrase un token existant', () => {
      setToken('first')
      setToken('second')
      expect(getToken()).toBe('second')
    })
  })

  describe('isAuthenticated', () => {
    it("retourne false quand aucun token n'est stocké", () => {
      expect(isAuthenticated()).toBe(false)
    })

    it('retourne true quand un token est stocké', () => {
      setToken('abc123')
      expect(isAuthenticated()).toBe(true)
    })

    it('retourne false après clearToken', () => {
      setToken('abc123')
      clearToken()
      expect(isAuthenticated()).toBe(false)
    })
  })
})