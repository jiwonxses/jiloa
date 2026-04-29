from fastapi import APIRouter, Depends, HTTPException, Header

from ..database import get_connection
from ..schemas import TokenResponse, UserLogin, UserPublic, UserRegister

import hashlib
import secrets



def hash_password(password: str, salt: str) -> str:
    """SHA-256 avec sel : hash(password + salt)."""
    return hashlib.sha256((password + salt).encode()).hexdigest()


def generate_salt() -> str:
    """Génère un sel aléatoire de 32 caractères hex."""
    return secrets.token_hex(16)


def generate_token() -> str:
    """Génère un token aléatoire de 64 caractères."""
    return secrets.token_urlsafe(48)


def get_current_user_id(x_token: str = Header(...)) -> int:
    """
    Dependency : extrait le token du header 'X-Token'.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM app_user WHERE token = %s;", (x_token,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(401, "Token invalide")
            return row[0]





router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=201)
def register(user: UserRegister) -> UserPublic:
    if not user.username or not user.password:
        raise HTTPException(400, "Username et password requis")

    salt = generate_salt()
    password_hash = hash_password(user.password, salt)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM app_user WHERE username = %s;", (user.username,))
            if cur.fetchone():
                raise HTTPException(400, "Username déjà utilisé")

            cur.execute(
                """
                INSERT INTO app_user (username, password_hash, salt)
                VALUES (%s, %s, %s)
                RETURNING id, username;
                """,
                (user.username, password_hash, salt),
            )
            row = cur.fetchone()
            conn.commit()

    return UserPublic(id=row[0], username=row[1])


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin) -> TokenResponse:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, password_hash, salt FROM app_user WHERE username = %s;",
                (credentials.username,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(401, "Identifiants invalides")

            user_id, stored_hash, salt = row
            computed_hash = hash_password(credentials.password, salt)
            if computed_hash != stored_hash:
                raise HTTPException(401, "Identifiants invalides")

            # Génère un nouveau token et le stocke
            token = generate_token()
            cur.execute(
                "UPDATE app_user SET token = %s WHERE id = %s;",
                (token, user_id),
            )
            conn.commit()

    return TokenResponse(token=token)


@router.get("/me", response_model=UserPublic)
def me(user_id: int = Depends(get_current_user_id)) -> UserPublic:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username FROM app_user WHERE id = %s;",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "User not found")
            return UserPublic(id=row[0], username=row[1])
        
        