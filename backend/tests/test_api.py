import os
import secrets
import httpx

BASE_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8001")


def random_username() -> str:
    return f"test_{secrets.token_hex(4)}"


def test_register_and_login_flow():
    """Register → login → access protected route."""
    username = random_username()
    
    r = httpx.post(f"{BASE_URL}/auth/register",
                   json={"username": username, "password": "pwd"})
    assert r.status_code == 201
    
    r = httpx.post(f"{BASE_URL}/auth/login",
                   json={"username": username, "password": "pwd"})
    assert r.status_code == 200
    token = r.json()["token"]
    
    r = httpx.get(f"{BASE_URL}/auth/me", headers={"X-Token": token})
    assert r.status_code == 200
    assert r.json()["username"] == username


def test_register_duplicate_fails():
    username = random_username()
    httpx.post(f"{BASE_URL}/auth/register", json={"username": username, "password": "x"})
    r = httpx.post(f"{BASE_URL}/auth/register", json={"username": username, "password": "y"})
    assert r.status_code == 400


def test_login_wrong_password():
    username = random_username()
    httpx.post(f"{BASE_URL}/auth/register", json={"username": username, "password": "good"})
    r = httpx.post(f"{BASE_URL}/auth/login",
                   json={"username": username, "password": "bad"})
    assert r.status_code == 401


def test_protected_route_no_token():
    r = httpx.get(f"{BASE_URL}/auth/me")
    assert r.status_code in (401, 422)


def test_search_by_title():
    """Recherche lexicale par titre (avec typo)."""
    r = httpx.get(f"{BASE_URL}/movies/search?q=Inceptio&limit=3")
    assert r.status_code == 200
    titles = [m["title"] for m in r.json()]
    assert any("Inception" in t for t in titles)


def test_search_semantic():
    """Recherche sémantique."""
    r = httpx.get(f"{BASE_URL}/movies/search/multi?q=space+exploration&limit=3")
    assert r.status_code == 200
    data = r.json()
    assert len(data["pure"]) > 0


def test_favorites_flow():
    """Ajouter un favori, le retrouver dans la liste."""
    username = random_username()
    httpx.post(f"{BASE_URL}/auth/register",
               json={"username": username, "password": "pwd"})
    login = httpx.post(f"{BASE_URL}/auth/login",
                       json={"username": username, "password": "pwd"})
    token = login.json()["token"]
    headers = {"X-Token": token}
    
    # Prendre n'importe quel film de la DB de test
    search = httpx.get(f"{BASE_URL}/movies/search/multi?q=action&limit=1")
    movie_id = search.json()["pure"][0]["id"]
    
    r = httpx.post(f"{BASE_URL}/favorites/{movie_id}", headers=headers)
    assert r.status_code == 201
    
    r = httpx.get(f"{BASE_URL}/favorites", headers=headers)
    assert any(m["id"] == movie_id for m in r.json())


def test_recommendations():
    """Avec quelques favoris, on doit recevoir des recos."""
    username = random_username()
    httpx.post(f"{BASE_URL}/auth/register",
               json={"username": username, "password": "pwd"})
    login = httpx.post(f"{BASE_URL}/auth/login",
                       json={"username": username, "password": "pwd"})
    token = login.json()["token"]
    headers = {"X-Token": token}
    
    # Ajouter 3 favoris
    search = httpx.get(f"{BASE_URL}/movies/search/multi?q=action&limit=3")
    for movie in search.json()["pure"]:
        httpx.post(f"{BASE_URL}/favorites/{movie['id']}", headers=headers)
    
    r = httpx.get(f"{BASE_URL}/favorites/recommendations?limit=5", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) > 0