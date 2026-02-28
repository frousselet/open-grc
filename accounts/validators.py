import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexityValidator:
    """
    Validate that the password contains at least one uppercase letter,
    one lowercase letter, one digit, and one special character (RA-02).
    """

    def validate(self, password, user=None):
        errors = []
        if not re.search(r"[A-Z]", password):
            errors.append(
                _("The password must contain at least one uppercase letter.")
            )
        if not re.search(r"[a-z]", password):
            errors.append(
                _("The password must contain at least one lowercase letter.")
            )
        if not re.search(r"\d", password):
            errors.append(
                _("The password must contain at least one digit.")
            )
        if not re.search(r"[^A-Za-z0-9]", password):
            errors.append(
                _("The password must contain at least one special character.")
            )
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _(
            "The password must contain at least one uppercase letter, "
            "one lowercase letter, one digit, and one special character."
        )
