from rest_framework.throttling import AnonRateThrottle


class LoginAnonThrottle(AnonRateThrottle):
    """Brute-force protection on credential grant."""

    scope = "login"


class RefreshAnonThrottle(AnonRateThrottle):
    """Limits refresh-token abuse (credential stuffing / replay attempts)."""

    scope = "refresh"
