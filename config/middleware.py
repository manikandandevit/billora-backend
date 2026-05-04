"""Response tweaks for paths not covered by typical API conventions."""


class MediaCrossOriginMiddleware:
    """
    Uploaded files are served under /media/ for the SPA on another origin (e.g. Vercel).
    CORP can block <img> cross-origin; allow embedding and simple CORS for GET.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith("/media/"):
            return response
        response["Cross-Origin-Resource-Policy"] = "cross-origin"
        response["Access-Control-Allow-Origin"] = "*"
        return response
