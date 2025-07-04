from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.templating import Jinja2Templates
from db import init_db
from modules.login import verify_user, get_user_roles, assign_role
from modules.auth_utils import hash_password
from modules.roles import Role
from modules.audit import log_action
from ..utils import get_db

router = APIRouter()

class AuthMiddleware(BaseHTTPMiddleware):
    """Redirect anonymous users to the login page."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/static") or path in {"/login", "/register", "/health"}:
            return await call_next(request)
        if not ensure_logged_in(request):
            return RedirectResponse("/login")
        if "roles" not in request.session:
            conn, cursor = init_db()
            request.session["roles"] = get_user_roles(cursor, request.session.get("user_id"))
            conn.close()
        return await call_next(request)


def ensure_logged_in(request: Request) -> bool:
    """Return True if the current session is authenticated."""
    return bool(request.session.get("user_id"))


def user_has_role(request: Request, cursor, role: Role) -> bool:
    """Check if current session user has the given role."""
    user_id = request.session.get("user_id")
    if not user_id:
        return False
    cursor.execute(
        """
        SELECT 1 FROM user_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.user_id = ? AND r.name = ?
        """,
        (user_id, role.value),
    )
    return cursor.fetchone() is not None


def require_roles(*roles: Role):
    """Dependency ensuring the current user has any of the given roles."""

    def wrapper(request: Request, db=Depends(get_db)) -> None:
        _, cursor = db
        if not any(user_has_role(request, cursor, role) for role in roles):
            raise HTTPException(status_code=403, detail="Forbidden")

    return wrapper


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...), db=Depends(get_db)):
    conn, cursor = db
    user_id, imone = verify_user(conn, cursor, username, password)
    if user_id:
        request.session["user_id"] = user_id
        request.session["username"] = username
        request.session["imone"] = imone
        request.session["roles"] = get_user_roles(cursor, user_id)
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Neteisingi prisijungimo duomenys"}, status_code=400
    )


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None, "msg": None})


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    vardas: str = Form(""),
    pavarde: str = Form(""),
    pareigybe: str = Form(""),
    grupe: str = Form(""),
    imone: str = Form(""),
    db=Depends(get_db),
):
    conn, cursor = db
    cursor.execute("SELECT 1 FROM users WHERE username=?", (username,))
    if cursor.fetchone():
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Toks vartotojas jau egzistuoja", "msg": None},
            status_code=400,
        )
    pw_hash = hash_password(password)
    cursor.execute(
        "INSERT INTO users (username, password_hash, imone, vardas, pavarde, pareigybe, grupe, aktyvus) VALUES (?,?,?,?,?,?,?,0)",
        (username, pw_hash, imone or None, vardas, pavarde, pareigybe, grupe),
    )
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), "register", "users", cursor.lastrowid)
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "error": None, "msg": "Paraiška pateikta"},
    )


@router.get("/api/me")
def current_user(request: Request):
    """Grąžina prisijungusio vartotojo informaciją."""
    if not ensure_logged_in(request):
        raise HTTPException(status_code=401, detail="Nepatvirtintas vartotojas")
    return {
        "username": request.session.get("username"),
        "imone": request.session.get("imone"),
        "roles": request.session.get("roles", []),
    }


templates = Jinja2Templates(directory="web_app/templates")
