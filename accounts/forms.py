import base64

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import gettext_lazy as _

from accounts.models import Group, User
from helpers.image_utils import generate_image_variants


def _file_to_data_uri(uploaded_file):
    """Convert an uploaded file to a base64 data URI string."""
    data = base64.b64encode(uploaded_file.read()).decode()
    return f"data:{uploaded_file.content_type};base64,{data}"


def _set_avatar_with_variants(user, data_uri):
    """Set the avatar field and generate 16/32/64 variants."""
    user.avatar = data_uri
    variants = generate_image_variants(data_uri)
    user.avatar_16 = variants[16]
    user.avatar_32 = variants[32]
    user.avatar_64 = variants[64]


def _clear_avatar(user):
    """Clear the avatar and all its variants."""
    user.avatar = ""
    user.avatar_16 = ""
    user.avatar_32 = ""
    user.avatar_64 = ""


class LoginForm(forms.Form):
    email = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(attrs={"class": "form-control", "autofocus": True}),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text=password_validation.password_validators_help_texts,
    )
    password2 = forms.CharField(
        label=_("Confirm password"),
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "job_title", "department", "phone", "language", "timezone", "is_active")
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "job_title": forms.TextInput(attrs={"class": "form-control"}),
            "department": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "language": forms.Select(attrs={"class": "form-select"}),
            "timezone": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_("The two password fields didn't match."))
        return p2

    def clean_password1(self):
        p1 = self.cleaned_data.get("password1")
        if p1:
            password_validation.validate_password(p1)
        return p1

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    avatar = forms.ImageField(
        label=_("Profile photo"),
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
    )
    avatar_resized = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "job_title", "department", "phone", "language", "timezone", "is_active")
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "job_title": forms.TextInput(attrs={"class": "form-control"}),
            "department": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "language": forms.Select(attrs={"class": "form-select"}),
            "timezone": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        resized = self.cleaned_data.get("avatar_resized")
        if resized:
            _set_avatar_with_variants(user, resized)
        elif self.files.get("avatar"):
            _set_avatar_with_variants(user, _file_to_data_uri(self.files["avatar"]))
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """Form for users to edit their own profile (RU-04)."""

    avatar = forms.ImageField(
        label=_("Profile photo"),
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
    )
    avatar_resized = forms.CharField(required=False, widget=forms.HiddenInput())
    remove_avatar = forms.BooleanField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "language", "timezone")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "language": forms.Select(attrs={"class": "form-select"}),
            "timezone": forms.TextInput(attrs={"class": "form-control"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        resized = self.cleaned_data.get("avatar_resized")
        if self.cleaned_data.get("remove_avatar") and not resized and not self.files.get("avatar"):
            _clear_avatar(user)
        elif resized:
            _set_avatar_with_variants(user, resized)
        elif self.files.get("avatar"):
            _set_avatar_with_variants(user, _file_to_data_uri(self.files["avatar"]))
        if commit:
            user.save()
        return user


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ("name", "description")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        label=_("Current password"),
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text=password_validation.password_validators_help_texts,
    )
    new_password2 = forms.CharField(
        label=_("Confirm new password"),
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old = self.cleaned_data.get("old_password")
        if not self.user.check_password(old):
            raise forms.ValidationError(_("The current password is incorrect."))
        return old

    def clean_new_password2(self):
        p1 = self.cleaned_data.get("new_password1")
        p2 = self.cleaned_data.get("new_password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_("The two password fields didn't match."))
        if p1:
            password_validation.validate_password(p1, self.user)
        return p2

    def save(self):
        from django.utils import timezone

        self.user.set_password(self.cleaned_data["new_password1"])
        self.user.password_changed_at = timezone.now()
        self.user.save()
        return self.user
