"""OAuth client registry using Authlib.

Call configure_oauth() during app startup to register the Google provider.
The ``oauth`` instance is imported by route handlers for authorize_redirect /
authorize_access_token.
"""

from authlib.integrations.starlette_client import OAuth

from app.core.config import get_settings

oauth = OAuth()


def configure_oauth() -> None:
    """Register OAuth providers with their client credentials.

    Google uses OpenID Connect (userinfo comes from the token response).
    """
    settings = get_settings()

    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url=(
            "https://accounts.google.com/.well-known/openid-configuration"
        ),
        client_kwargs={"scope": "openid email profile"},
    )
