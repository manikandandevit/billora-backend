from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BranchSelfProfileView,
    BranchViewSet,
    ClientViewSet,
    HeadProfileView,
    PublicBrandingView,
    SubscriptionAlertsView,
)

router = DefaultRouter()
router.register("clients", ClientViewSet, basename="org-client")
router.register("branches", BranchViewSet, basename="org-branch")

urlpatterns = [
    path("branding/", PublicBrandingView.as_view(), name="org-branding"),
    path("head/", HeadProfileView.as_view(), name="org-head-profile"),
    path("branch/me/", BranchSelfProfileView.as_view(), name="org-branch-me"),
    path("subscription-alerts/", SubscriptionAlertsView.as_view(), name="org-subscription-alerts"),
    path("", include(router.urls)),
]
