from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .absolute_urls import public_absolute_uri
from .models import Branch, Client, Head
from .permissions import IsBranch, IsHead, IsHeadOrClient
from .serializers import (
    BranchCreateSerializer,
    BranchListSerializer,
    BranchSelfUpdateSerializer,
    BranchUpdateSerializer,
    ClientCreateSerializer,
    ClientListSerializer,
    ClientUpdateSerializer,
    HeadProfileSerializer,
    HeadProfileUpdateSerializer,
)


def org_head_from_request(request) -> Head | None:
    """Head row for the authenticated org manager (either Head login or linked Client staff)."""
    u = request.user
    hp = getattr(u, "head_profile", None)
    if hp is not None:
        return hp
    cp = getattr(u, "client_profile", None)
    return cp.head if cp is not None else None


class PublicBrandingView(APIView):
    """Public logo URL for login / tab (single Head tenant). No auth."""

    permission_classes = [AllowAny]

    def get(self, request):
        head = Head.objects.order_by("pk").first()
        logo_url = None
        if head and head.company_logo:
            logo_url = public_absolute_uri(request, head.company_logo.url)
        return Response({"company_logo_url": logo_url, "app_name": "Billora"})


class HeadProfileView(APIView):
    """Current Head: read profile; update password and/or company logo (not email)."""

    permission_classes = [IsAuthenticated, IsHead]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        ser = HeadProfileSerializer(request.user.head_profile, context={"request": request})
        return Response(ser.data)

    def patch(self, request):
        head = request.user.head_profile
        ser = HeadProfileUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save(head=head)
        head.refresh_from_db()
        return Response(HeadProfileSerializer(head, context={"request": request}).data)


class SubscriptionAlertsView(APIView):
    """
    Clients whose subscription_end is within the next 3 days (inclusive of today).
    Used for the Head Email tab; matches the 3-day email reminder window.
    """

    permission_classes = [IsAuthenticated, IsHead]

    def get(self, request):
        today = timezone.localdate()
        window_end = today + timedelta(days=3)
        clients = (
            Client.objects.filter(
                head=request.user.head_profile,
                subscription_end__isnull=False,
                subscription_end__gte=today,
                subscription_end__lte=window_end,
            )
            .select_related("user")
            .order_by("subscription_end", "user__email")
        )
        rows = []
        for c in clients:
            rows.append(
                {
                    "id": c.id,
                    "name": (c.name or "").strip() or c.user.email,
                    "phone": (c.phone or "").strip(),
                    "email": c.user.email,
                    "subscription_type": c.subscription_type,
                    "subscription_label": c.get_subscription_type_display(),
                    "subscription_end": c.subscription_end.isoformat() if c.subscription_end else None,
                    "days_remaining": (c.subscription_end - today).days if c.subscription_end else None,
                }
            )
        return Response({"alerts": rows})


class ClientViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, IsHead]

    def get_queryset(self):
        qs = Client.objects.filter(head=self.request.user.head_profile).select_related("user")
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(user__email__icontains=search) | Q(name__icontains=search) | Q(phone__icontains=search)
            )
        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return ClientCreateSerializer
        if self.action in ("update", "partial_update"):
            return ClientUpdateSerializer
        return ClientListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["head"] = self.request.user.head_profile
        return ctx

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = serializer.save()
        out = ClientListSerializer(client, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        instance.refresh_from_db()
        return Response(ClientListSerializer(instance, context=self.get_serializer_context()).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class BranchViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, IsHeadOrClient]

    def get_queryset(self):
        head_org = org_head_from_request(self.request)
        if head_org is None:
            return Branch.objects.none()
        qs = Branch.objects.filter(head=head_org).select_related("user")
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(hotel_name__icontains=search)
                | Q(owner_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(address__icontains=search)
                | Q(user__email__icontains=search)
            )
        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return BranchCreateSerializer
        if self.action in ("update", "partial_update"):
            return BranchUpdateSerializer
        return BranchListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["head"] = org_head_from_request(self.request)
        return ctx

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        branch = serializer.save()
        out = BranchListSerializer(branch, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        instance.refresh_from_db()
        return Response(BranchListSerializer(instance, context=self.get_serializer_context()).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class BranchSelfProfileView(APIView):
    """Current branch outlet: read and update hotel details + password."""

    permission_classes = [IsAuthenticated, IsBranch]

    def get(self, request):
        branch = request.user.branch_profile
        return Response(BranchListSerializer(branch, context={"request": request}).data)

    def patch(self, request):
        branch = request.user.branch_profile
        serializer = BranchSelfUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.update(branch, serializer.validated_data)
        branch.refresh_from_db()
        return Response(BranchListSerializer(branch, context={"request": request}).data)
