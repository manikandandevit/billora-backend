"""Stable absolute URLs for media when the API sits behind a proxy (Render) and JSON is consumed from another origin (Vercel)."""

from django.conf import settings


def public_absolute_uri(request, path: str) -> str:
    """
    Join PUBLIC_API_BASE_URL + path when set.
    Else prefer X-Forwarded-Proto / X-Forwarded-Host (Render) so URLs are https + public host.
    Fallback: request.build_absolute_uri(path).
    """
    if not path.startswith("/"):
        path = "/" + path
    base = getattr(settings, "PUBLIC_API_BASE_URL", "") or ""
    base = base.strip().rstrip("/")
    if base:
        return f"{base}{path}"
    forwarded_proto = (request.headers.get("X-Forwarded-Proto") or "").strip()
    forwarded_host = (request.headers.get("X-Forwarded-Host") or "").strip()
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}{path}"
    return request.build_absolute_uri(path)
