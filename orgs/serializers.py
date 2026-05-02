from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import Branch, Client, Head, SubscriptionType


class HeadProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    company_logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Head
        fields = (
            "id",
            "email",
            "company_logo",
            "company_logo_url",
        )
        read_only_fields = (
            "id",
            "email",
            "company_logo",
            "company_logo_url",
        )

    def get_company_logo_url(self, obj: Head) -> str | None:
        request = self.context.get("request")
        if not obj.company_logo or not request:
            return None
        return request.build_absolute_uri(obj.company_logo.url)


class HeadProfileUpdateSerializer(serializers.Serializer):
    """Password and/or company logo (multipart). Email is not changed here."""

    password = serializers.CharField(write_only=True, min_length=8, required=False, allow_blank=True)
    company_logo = serializers.ImageField(required=False, allow_null=False)

    def validate(self, attrs):
        pwd = (attrs.get("password") or "").strip()
        if not pwd and "company_logo" not in attrs:
            raise serializers.ValidationError("Send at least one of: password, company_logo.")
        return attrs

    def save(self, **kwargs):
        head: Head = kwargs["head"]
        user = head.user
        pwd = (self.validated_data.get("password") or "").strip()
        if pwd:
            user.set_password(pwd)
            user.save(update_fields=["password"])
        if "company_logo" in self.validated_data:
            head.company_logo = self.validated_data["company_logo"]
            head.save(update_fields=["company_logo"])
        return head


class ClientListSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    subscription_label = serializers.CharField(source="get_subscription_type_display", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)

    class Meta:
        model = Client
        fields = (
            "id",
            "name",
            "phone",
            "email",
            "subscription_type",
            "subscription_label",
            "subscription_end",
            "created_at",
            "is_active",
        )


class ClientCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    subscription_type = serializers.ChoiceField(choices=SubscriptionType.choices, required=False)

    def validate_email(self, value: str) -> str:
        User = get_user_model()
        if User.objects.filter(email__iexact=value.strip().lower()).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.strip().lower()

    def create(self, validated_data):
        User = get_user_model()
        head: Head = self.context["head"]
        user = User(email=validated_data["email"])
        user.set_password(validated_data["password"])
        user.save()
        client = Client.objects.create(
            head=head,
            user=user,
            name=(validated_data.get("name") or "").strip(),
            phone=(validated_data.get("phone") or "").strip()[:32],
            subscription_type=validated_data.get("subscription_type") or SubscriptionType.MONTHLY,
        )
        from orgs.subscription_access import apply_org_subscription_state

        apply_org_subscription_state(head.pk)
        return client


class ClientUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=128)
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    subscription_type = serializers.ChoiceField(choices=SubscriptionType.choices, required=False)

    def validate_email(self, value: str | None) -> str | None:
        if value is None:
            return None
        User = get_user_model()
        v = value.strip().lower()
        user = self.instance.user
        if User.objects.filter(email__iexact=v).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("Another account already uses this email.")
        return v

    def validate_password(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            return ""
        if len(v) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters.")
        return v

    def update(self, instance: Client, validated_data):
        user = instance.user
        old_subscription_type = instance.subscription_type
        plan_type_changed = (
            "subscription_type" in validated_data
            and validated_data["subscription_type"] != old_subscription_type
        )

        if "email" in validated_data and validated_data["email"] is not None:
            user.email = validated_data["email"]
            user.save(update_fields=["email"])
        pwd = (validated_data.pop("password", "") or "").strip()
        if pwd:
            user.set_password(pwd)
            user.save()

        if "phone" in validated_data:
            instance.phone = (validated_data["phone"] or "").strip()[:32]

        for field in ("name", "subscription_type"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        if plan_type_changed:
            instance.expiry_reminder_sent = False
            instance.subscription_period_start = timezone.localdate()

        instance.save()
        from orgs.subscription_access import apply_org_subscription_state

        apply_org_subscription_state(instance.head_id)
        return instance


class BranchListSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)

    class Meta:
        model = Branch
        fields = (
            "id",
            "head_id",
            "hotel_name",
            "owner_name",
            "phone",
            "address",
            "email",
            "salespoints_slug",
            "created_at",
            "is_active",
            "paused_by_head",
        )


class BranchCreateSerializer(serializers.Serializer):
    hotel_name = serializers.CharField(max_length=200)
    owner_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        User = get_user_model()
        if User.objects.filter(email__iexact=value.strip().lower()).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.strip().lower()

    def create(self, validated_data):
        User = get_user_model()
        head: Head = self.context["head"]
        user = User(email=validated_data["email"])
        user.set_password(validated_data["password"])
        user.save()
        slug = Branch.allocate_salespoints_slug(validated_data["hotel_name"])
        branch = Branch.objects.create(
            head=head,
            user=user,
            hotel_name=validated_data["hotel_name"].strip(),
            owner_name=(validated_data.get("owner_name") or "").strip()[:200],
            phone=(validated_data.get("phone") or "").strip()[:32],
            address=(validated_data.get("address") or "").strip(),
            salespoints_slug=slug,
        )
        from orgs.subscription_access import apply_org_subscription_state

        apply_org_subscription_state(head.pk)
        return branch


class BranchUpdateSerializer(serializers.Serializer):
    """Head editing a branch outlet."""

    hotel_name = serializers.CharField(max_length=200, required=False)
    owner_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=128)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)

    def validate_email(self, value: str | None) -> str | None:
        if value is None:
            return None
        User = get_user_model()
        v = value.strip().lower()
        user = self.instance.user
        if User.objects.filter(email__iexact=v).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("Another account already uses this email.")
        return v

    def validate_password(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            return ""
        if len(v) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters.")
        return v

    def update(self, instance: Branch, validated_data: dict):
        user = instance.user

        if "email" in validated_data and validated_data["email"] is not None:
            user.email = validated_data["email"]
            user.save(update_fields=["email"])

        pwd = ((validated_data.get("password")) or "").strip()
        if pwd:
            user.set_password(pwd)
            user.save()

        if "is_active" in validated_data:
            active = validated_data["is_active"]
            user.is_active = active
            user.save(update_fields=["is_active"])
            instance.paused_by_head = not active

        if "hotel_name" in validated_data:
            instance.hotel_name = validated_data["hotel_name"].strip()[:200]
        if "owner_name" in validated_data:
            instance.owner_name = (validated_data["owner_name"] or "").strip()[:200]
        if "phone" in validated_data:
            instance.phone = (validated_data["phone"] or "").strip()[:32]
        if "address" in validated_data:
            instance.address = (validated_data["address"] or "").strip()

        instance.save()
        return instance


class BranchSelfUpdateSerializer(serializers.Serializer):
    """Branch staff updating their outlet profile (+ password); email not editable here."""

    hotel_name = serializers.CharField(max_length=200, required=False)
    owner_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate_password(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            return ""
        if len(v) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters.")
        return v

    def update(self, instance: Branch, validated_data: dict) -> Branch:
        pwd = (validated_data.get("password") or "").strip()
        if pwd:
            instance.user.set_password(pwd)
            instance.user.save(update_fields=["password"])

        if "hotel_name" in validated_data:
            instance.hotel_name = validated_data["hotel_name"].strip()[:200]
        if "owner_name" in validated_data:
            instance.owner_name = (validated_data["owner_name"] or "").strip()[:200]
        if "phone" in validated_data:
            instance.phone = (validated_data["phone"] or "").strip()[:32]
        if "address" in validated_data:
            instance.address = (validated_data["address"] or "").strip()

        instance.save()
        return instance
