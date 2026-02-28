import factory
from django.contrib.auth import get_user_model

from accounts.models import Group, Permission

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "testpass123")
        user = model_class(*args, **kwargs)
        user.set_password(password)
        user.save()
        return user


class PermissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Permission
        django_get_or_create = ("codename",)

    codename = factory.Sequence(lambda n: f"test.feature{n}.read")
    name = factory.LazyAttribute(lambda o: o.codename)
    module = factory.LazyAttribute(lambda o: o.codename.split(".")[0])
    feature = factory.LazyAttribute(lambda o: o.codename.split(".")[1])
    action = factory.LazyAttribute(lambda o: o.codename.split(".")[2])


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = factory.Sequence(lambda n: f"Group {n}")
