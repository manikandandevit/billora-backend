"""Stable absolute URLs for media when the API sits behind a proxy (Render) and JSON is consumed from another origin (Vercel)."""

from django.conf import settings


def public_absolute_uri(request, path: str) -> str:
    """
    Join PUBLIC_API_BASE_URL + path when set; else request.build_absolute_uri(path).
    `path` is typically from FileField.url (e.g. /media/company_logos/...).
    """
    if not path.startswith("/"):
        path = "/" + path
    base = getattr(settings, "PUBLIC_API_BASE_URL", "") or ""
    base = base.strip().rstrip("/")
    if base:
        return f"{base}{path}"
    return request.build_absolute_uri(path)
