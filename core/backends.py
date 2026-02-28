from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """Authenticate with either username or email."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        # Try username first
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Try email
            try:
                user = User.objects.get(email__iexact=username)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
