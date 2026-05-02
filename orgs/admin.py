from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import Branch, Client, Head


class HeadAdminForm(forms.ModelForm):
    email = forms.EmailField(label="Email")
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(render_value=False),
        required=False,
        help_text="Required when creating a new Head. Leave blank to keep the current password.",
    )

    class Meta:
        model = Head
        fields = ("company_logo",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company_logo"].label = "Billora company logo"
        if self.instance.pk and self.instance.user_id:
            self.fields["email"].initial = self.instance.user.email

    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk and Head.objects.exists():
            raise forms.ValidationError(
                "Only one Billora Head is allowed. Edit the existing Head, or delete it before creating another."
            )
        if not self.instance.pk and not (cleaned.get("password") or "").strip():
            raise forms.ValidationError({"password": "Password is required for a new Head."})
        return cleaned

    def save(self, commit=True):
        head = self.instance
        if "company_logo" in self.cleaned_data:
            head.company_logo = self.cleaned_data["company_logo"]

        User = get_user_model()
        email = self.cleaned_data["email"].strip().lower()
        password = (self.cleaned_data.get("password") or "").strip()

        if head.pk and head.user_id:
            user = head.user
            if password:
                user.set_password(password)
            if user.email != email:
                if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
                    raise forms.ValidationError({"email": "Another user already has this email."})
                user.email = email
            user.save()
        else:
            if User.objects.filter(email__iexact=email).exists():
                raise forms.ValidationError({"email": "A user with this email already exists."})
            user = User(email=email)
            user.set_password(password)
            user.save()
            head.user = user

        if commit:
            head.save()
        return head


@admin.register(Head)
class HeadAdmin(admin.ModelAdmin):
    form = HeadAdminForm
    search_fields = ("user__email",)
    list_display = ("user_email",)

    def get_fieldsets(self, request, obj=None):
        return (
            ("Head login", {"fields": ("email", "password")}),
            ("Billora company logo", {"fields": ("company_logo",)}),
        )

    @admin.display(description="Email")
    def user_email(self, obj: Head) -> str:
        if not obj.user_id:
            return "—"
        return obj.user.email

    def has_add_permission(self, request):
        if not super().has_add_permission(request):
            return False
        return not Head.objects.exists()

    def save_form(self, request, form, change):
        """HeadAdminForm persists user + head in one step; skip the default commit=False path."""
        if isinstance(form, HeadAdminForm):
            return form.save(commit=True)
        return super().save_form(request, form, change)

    def save_model(self, request, obj, form, change):
        if isinstance(form, HeadAdminForm):
            return
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        # HeadAdminForm uses save(commit=True); Django never binds save_m2m(), but admin always calls it.
        # Head has no M2M fields — skip this step for our form.
        if isinstance(form, HeadAdminForm):
            return
        super().save_related(request, form, formsets, change)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "display_name",
        "user_email",
        "phone",
        "head",
        "subscription_type",
        "subscription_end",
        "created_at",
    )
    list_filter = ("head", "subscription_type",)
    search_fields = ("user__email", "name", "phone", "head__user__email")
    autocomplete_fields = ("head", "user")

    @admin.display(description="Client email")
    def user_email(self, obj: Client) -> str:
        return obj.user.email

    @admin.display(description="Name")
    def display_name(self, obj: Client) -> str:
        return (obj.name or "").strip() or "—"


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("id", "hotel_name", "user_email", "salespoints_slug", "head", "created_at")
    search_fields = ("hotel_name", "owner_name", "user__email", "salespoints_slug")
    list_filter = ("head",)
    autocomplete_fields = ("head", "user")
    readonly_fields = ("salespoints_slug", "created_at")

    @admin.display(description="Login email")
    def user_email(self, obj: Branch) -> str:
        return obj.user.email
