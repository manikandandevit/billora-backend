from rest_framework_simplejwt.authentication import JWTAuthentication

from rest_framework.exceptions import AuthenticationFailed

from orgs.subscription_access import subscription_denial_reason_for_user


def _prefetch_subscription_profiles(user):
    if not user.pk:
        return user
    cls = user.__class__
    try:
        return cls.objects.select_related(
            "head_profile",
            "branch_profile",
            "client_profile",
        ).get(pk=user.pk)
    except cls.DoesNotExist:
        return user


class SubscriptionEnforcingJWTAuthentication(JWTAuthentication):
    """
    After Bearer validation, apply the same org subscription rules as Login + Refresh
    so access tokens can't keep calling APIs after the billing window closes.
    """

    def authenticate(self, request):
        pair = super().authenticate(request)
        if pair is None:
            return pair
        user, validated_token = pair
        user = _prefetch_subscription_profiles(user)
        denial = subscription_denial_reason_for_user(user)
        if denial:
            raise AuthenticationFailed(
                detail=denial,
                code="subscription_denied",
            )
        return user, validated_token
