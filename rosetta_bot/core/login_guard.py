"""
Login-flow guards shared by the sync browser bot and the async fast runner.

Institutional ``@live.uleam.edu.ec`` accounts authenticate through Microsoft.
On a new device/IP Microsoft may interrupt the password flow with an extra
verification screen (MFA, code, CAPTCHA, "help us protect your account")
that the bot cannot complete. These helpers detect that situation so both
login flows fail loudly instead of continuing unauthenticated — which
previously surfaced only much later as ``login?reauth=true`` redirects and
"story list did not render" timeouts.
"""

from typing import Optional

# URL fragments that mean we are still inside a login/authentication flow.
_LOGIN_URL_MARKERS = (
    "login.rosettastone.com/login",
    "login.microsoftonline.com",
    "login.live.com",
)

# (marker, human-readable reason) — matched against lowercase visible text.
_BLOCKER_MARKERS = (
    ("verify your identity", "Microsoft asks to verify your identity (MFA)"),
    ("comprueba tu identidad", "Microsoft pide verificar tu identidad (MFA)"),
    ("verifica tu identidad", "Microsoft pide verificar tu identidad (MFA)"),
    ("approve sign in", "Microsoft asks to approve the sign-in request (MFA)"),
    ("aprueba la solicitud", "Microsoft pide aprobar la solicitud de inicio de sesión (MFA)"),
    ("authenticator", "Microsoft Authenticator verification required"),
    ("enter the code", "A verification code is required"),
    ("escribe el código", "Se requiere un código de verificación"),
    ("escriba el código", "Se requiere un código de verificación"),
    ("help us protect", "Microsoft account-protection check is blocking the login"),
    ("proteger tu cuenta", "Una comprobación de protección de la cuenta Microsoft bloquea el login"),
    ("unusual activity", "Microsoft flagged unusual activity on the account"),
    ("actividad inusual", "Microsoft detectó actividad inusual en la cuenta"),
    ("captcha", "A CAPTCHA challenge is shown"),
    ("your account or password is incorrect", "Wrong email or password"),
    ("la cuenta o la contraseña no son correctas", "Email o contraseña incorrectos"),
)

# Markers of Microsoft's "Stay signed in?" (KMSI) prompt.
KMSI_MARKERS = (
    "stay signed in",
    "mantener la sesión iniciada",
    "mantener sesión iniciada",
    "quiere mantener la sesión",
)

MANUAL_LOGIN_HINT = (
    "Fix: set BROWSER_HEADLESS=0 in the .env, run once, and complete the "
    "verification manually in the browser window that opens. The login "
    "session will be saved and reused automatically on later runs."
)


def is_login_url(url: str) -> bool:
    """True while *url* still belongs to a login/authentication page."""
    return any(marker in url for marker in _LOGIN_URL_MARKERS)


def find_login_blocker(visible_text: str) -> Optional[str]:
    """
    Return a human-readable description of the screen blocking the login,
    or ``None`` when no known blocker is present in *visible_text*.
    """
    lowered = visible_text.lower()
    for marker, reason in _BLOCKER_MARKERS:
        if marker in lowered:
            return reason
    return None


def is_kmsi_prompt(visible_text: str) -> bool:
    """True when *visible_text* shows Microsoft's 'Stay signed in?' prompt."""
    lowered = visible_text.lower()
    return any(marker in lowered for marker in KMSI_MARKERS)
