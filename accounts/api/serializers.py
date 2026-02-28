from django.contrib.auth import password_validation
from rest_framework import serializers

from accounts.models import AccessLog, Group, Permission, User
from context.models import Scope


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "codename", "name", "module", "feature", "action", "is_system")
        read_only_fields = fields


class UserListSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    groups = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "email", "first_name", "last_name", "display_name",
            "job_title", "department", "is_active", "last_login", "groups",
        )
        read_only_fields = ("id", "display_name", "last_login")

    def get_groups(self, obj):
        return list(obj.custom_groups.values_list("name", flat=True))


class UserDetailSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    groups = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "email", "first_name", "last_name", "display_name",
            "job_title", "department", "phone", "language", "timezone",
            "is_active", "is_staff", "last_login", "created_at", "updated_at",
            "groups", "permissions",
        )
        read_only_fields = ("id", "display_name", "last_login", "created_at", "updated_at", "permissions")

    def get_groups(self, obj):
        return [{"id": str(g.id), "name": g.name} for g in obj.custom_groups.all()]

    def get_permissions(self, obj):
        return sorted(
            Permission.objects.filter(groups__users=obj).values_list("codename", flat=True).distinct()
        )


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "id", "email", "first_name", "last_name", "password",
            "job_title", "department", "phone", "language", "timezone",
            "is_active",
        )
        read_only_fields = ("id",)

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            user.created_by = request.user
        user.save()
        return user


class GroupSerializer(serializers.ModelSerializer):
    permissions = serializers.SlugRelatedField(
        slug_field="codename",
        queryset=Permission.objects.all(),
        many=True,
        required=False,
    )
    allowed_scopes = serializers.PrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=Scope.objects.all(),
    )
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = (
            "id", "name", "description", "is_system", "permissions",
            "allowed_scopes", "user_count", "created_at", "updated_at",
        )
        read_only_fields = ("id", "is_system", "created_at", "updated_at")

    def get_user_count(self, obj):
        return obj.users.count()


class AccessLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True, default=None)

    class Meta:
        model = AccessLog
        fields = (
            "id", "timestamp", "user", "user_email", "email_attempted",
            "event_type", "ip_address", "user_agent", "failure_reason", "metadata",
        )
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class MeSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "email", "first_name", "last_name", "display_name",
            "job_title", "department", "phone", "language", "timezone",
            "permissions",
        )
        read_only_fields = ("id", "email", "display_name", "permissions")

    def get_permissions(self, obj):
        return sorted(
            Permission.objects.filter(groups__users=obj).values_list("codename", flat=True).distinct()
        )
