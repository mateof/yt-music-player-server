"""Router de autenticación para YouTube Music."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.auth import get_auth_status, save_credentials, logout

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Request para login con headers del navegador."""
    headers_raw: str


class AuthResponse(BaseModel):
    """Respuesta de autenticación."""
    success: bool
    message: str


class AuthStatusResponse(BaseModel):
    """Respuesta de estado de autenticación."""
    authenticated: bool
    message: str


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status():
    """Verificar el estado de autenticación actual."""
    return get_auth_status()


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Iniciar sesión con headers del navegador o cookies.
    Acepta: headers raw, cookies JSON (EditThisCookie), o cookies string.
    """
    if not request.headers_raw or len(request.headers_raw.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Datos vacíos. Pega las cookies o headers copiados."
        )

    print(f"[AUTH] Recibido input de {len(request.headers_raw)} caracteres")
    print(f"[AUTH] Primeros 100 chars: {request.headers_raw[:100]}...")

    result = save_credentials(request.headers_raw)

    print(f"[AUTH] Resultado: {result}")

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.post("/logout", response_model=AuthResponse)
async def do_logout():
    """Cerrar sesión y eliminar credenciales guardadas."""
    return logout()
