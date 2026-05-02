from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from .throttles import LoginAnonThrottle, RefreshAnonThrottle


def _me_payload(user, request=None):
    from orgs.serializers import BranchListSerializer, HeadProfileSerializer

    payload = {
        "id": user.pk,
        "email": user.email,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "role": "none",
        "head": None,
        "branch": None,
        "client": None,
    }
    head = getattr(user, "head_profile", None)
    branch = getattr(user, "branch_profile", None)
    client = getattr(user, "client_profile", None)
    if head:
        payload["role"] = "head"
        payload["head"] = HeadProfileSerializer(head, context={"request": request}).data
    elif branch:
        payload["role"] = "branch"
        payload["branch"] = BranchListSerializer(branch, context={"request": request}).data
    elif client:
        payload["role"] = "client"
        payload["client"] = {
            "id": client.pk,
            "head_id": client.head_id,
            "email": client.user.email,
        }
    elif user.is_superuser:
        payload["role"] = "superuser"
    elif user.is_staff:
        payload["role"] = "staff"
    return payload


def _attach_jwt_claims(refresh: RefreshToken, user) -> str:
    head = getattr(user, "head_profile", None)
    branch = getattr(user, "branch_profile", None)
    client = getattr(user, "client_profile", None)
    if head:
        role = "head"
        refresh["head_id"] = head.pk
    elif branch:
        role = "branch"
        refresh["branch_id"] = branch.pk
        refresh["head_id"] = branch.head_id
    elif client:
        role = "client"
        refresh["client_id"] = client.pk
        refresh["head_id"] = client.head_id
    elif user.is_superuser:
        role = "superuser"
    elif user.is_staff:
        role = "staff"
    else:
        role = "none"
    refresh["role"] = role
    return role


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [RefreshAnonThrottle]

    def post(self, request, *args, **kwargs):
        refresh_str = request.data.get("refresh")
        if isinstance(refresh_str, str) and refresh_str.strip():
            try:
                token = RefreshToken(refresh_str)
            except TokenError:
                return super().post(request, *args, **kwargs)

            User = get_user_model()
            uid = token[jwt_settings.USER_ID_CLAIM]
            try:
                user = User.objects.select_related(
                    "head_profile",
                    "branch_profile",
                    "client_profile",
                ).get(pk=uid)
            except User.DoesNotExist:
                return super().post(request, *args, **kwargs)

            from orgs.subscription_access import subscription_denial_reason_for_user

            denial = subscription_denial_reason_for_user(user)
            if denial:
                try:
                    token.blacklist()
                except (AttributeError, NotImplementedError):
                    pass
                return Response({"detail": denial}, status=status.HTTP_403_FORBIDDEN)

        return super().post(request, *args, **kwargs)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginAnonThrottle]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""

        if not email:
            return Response(
                {"detail": "Please enter your email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not password:
            return Response(
                {"detail": "Please enter your password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        User = get_user_model()
        try:
            user_obj = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "Incorrect email or password. Please check and try again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = authenticate(request, email=user_obj.email, password=password)
        if user is None:
            if user_obj.check_password(password) and not user_obj.is_active:
                return Response(
                    {
                        "detail": (
                            "This account has been deactivated. "
                            "Contact your company Head if you need access again."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response(
                {"detail": "Incorrect email or password. Please check and try again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        head = getattr(user, "head_profile", None)
        branch_obj = getattr(user, "branch_profile", None)
        client = getattr(user, "client_profile", None)

        today = timezone.localdate()
        from orgs.subscription_access import (
            client_subscription_expired,
            freeze_organization_if_calendar_closed,
            organization_subscription_calendar_open,
        )

        if branch_obj:
            if not organization_subscription_calendar_open(branch_obj.head_id, today):
                freeze_organization_if_calendar_closed(branch_obj.head_id, today)
                return Response(
                    {
                        "detail": (
                            "Subscription ended for this company. "
                            "Branch logins stay off until your Head renews the client subscription."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif client:
            if client_subscription_expired(client, today):
                user.is_active = False
                user.save(update_fields=["is_active"])
                freeze_organization_if_calendar_closed(client.head_id, today)
                return Response(
                    {
                        "detail": (
                            "Your subscription has ended (demo / monthly / yearly window). "
                            "Ask your company Head to renew the plan — client and outlet logins reopen when the subscription is valid again."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        if (
            not head
            and not branch_obj
            and not client
            and not (user.is_staff or user.is_superuser)
        ):
            return Response(
                {
                    "detail": (
                        "This account is not linked to a Billora Head, Branch, or Client. "
                        "Ask your administrator to provision access."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        refresh = RefreshToken.for_user(user)
        refresh["email"] = user.email
        _attach_jwt_claims(refresh, user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "token_type": "Bearer",
                "access_expires_in": int(refresh.access_token.lifetime.total_seconds()),
                "refresh_expires_in": int(refresh.lifetime.total_seconds()),
                "user": _me_payload(user, request),
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_me_payload(request.user, request))
