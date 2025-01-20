from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext as _

from apps.users.models import MetaxUser


class OptionalPasswordUserCreationForm(UserCreationForm):
    """User creation form that allows omitting password to disable password auth."""

    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html(),
        required=False,
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
        required=False,
    )

    class Meta(UserCreationForm.Meta):
        model = MetaxUser

    def save(self, commit=True):
        user = super().save(commit=False)
        if password := self.cleaned_data["password1"]:
            user.set_password(password)
        else:
            # Password login is disabled for user
            user.set_unusable_password()
        if commit:
            user.save()
            if hasattr(self, "save_m2m"):
                self.save_m2m()
        return user
