from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.api.filters import AccessLogFilter, PermissionFilter, UserFilter
from accounts.api.permissions import ModulePermission
from accounts.api.serializers import (
    AccessLogSerializer,
    GroupSerializer,
    LoginSerializer,
    MeSerializer,
    PermissionSerializer,
    UserCreateSerializer,
    UserDetailSerializer,
    UserListSerializer,
)
from accounts.constants import AccessEventType, FailureReason
from accounts.models import AccessLog, Group, Permission, User


# ── Auth API Views ──────────────────────────────────────────

class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(request, username=email, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            # Log via signal fires from authenticate, but we need to
            # manually fire login signal for session-less JWT
            AccessLog.objects.create(
                user=user,
                email_attempted=email,
                event_type=AccessEventType.LOGIN_SUCCESS,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            user.reset_failed_attempts()

            permissions = sorted(
                Permission.objects.filter(groups__users=user).values_list("codename", flat=True).distinct()
            )
            return Response({
                "status": "success",
                "data": {
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "display_name": user.display_name,
                        "language": user.language,
                        "permissions": permissions,
                    },
                },
            })
        else:
            # Determine error type
            try:
                u = User.objects.get(email__iexact=email)
                if u.is_locked:
                    return Response({
                        "status": "error",
                        "error": {
                            "code": "ACCOUNT_LOCKED",
                            "message": "Le compte est temporairement verrouillé.",
                            "details": {
                                "locked_until": u.locked_until.isoformat() if u.locked_until else None,
                            },
                        },
                    }, status=status.HTTP_403_FORBIDDEN)
            except User.DoesNotExist:
                pass

            return Response({
                "status": "error",
                "error": {
                    "code": "AUTHENTICATION_FAILED",
                    "message": "Email ou mot de passe invalide.",
                },
            }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass

        AccessLog.objects.create(
            user=request.user,
            email_attempted=request.user.email,
            event_type=AccessEventType.LOGOUT,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        return Response({"status": "success"})


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user)
        return Response({"status": "success", "data": serializer.data})

    def patch(self, request):
        serializer = MeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": "success", "data": serializer.data})


class TokenRefreshAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response(
                {"status": "error", "error": {"code": "MISSING_TOKEN", "message": "refresh_token requis."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            old_refresh = RefreshToken(refresh_token)
            # Blacklist old token (rotation)
            old_refresh.blacklist()
            user_id = old_refresh["user_id"]
            user = User.objects.get(pk=user_id)
            new_refresh = RefreshToken.for_user(user)
            return Response({
                "status": "success",
                "data": {
                    "access_token": str(new_refresh.access_token),
                    "refresh_token": str(new_refresh),
                },
            })
        except Exception:
            return Response(
                {"status": "error", "error": {"code": "INVALID_TOKEN", "message": "Token invalide ou expiré."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )


# ── Resource ViewSets ───────────────────────────────────────

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "system"
    permission_feature = "users"
    filterset_class = UserFilter
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["email", "last_name", "created_at", "last_login"]

    def get_serializer_class(self):
        if self.action == "list":
            return UserListSerializer
        if self.action == "create":
            return UserCreateSerializer
        return UserDetailSerializer

    @action(detail=True, methods=["get"])
    def groups(self, request, pk=None):
        user = self.get_object()
        groups = user.custom_groups.all()
        serializer = GroupSerializer(groups, many=True)
        return Response({"status": "success", "data": serializer.data})

    @action(detail=True, methods=["get"])
    def permissions(self, request, pk=None):
        user = self.get_object()
        perms = sorted(
            Permission.objects.filter(groups__users=user).values_list("codename", flat=True).distinct()
        )
        return Response({"status": "success", "data": perms})


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "system"
    permission_feature = "groups"
    search_fields = ["name"]

    def destroy(self, request, *args, **kwargs):
        group = self.get_object()
        if group.is_system:
            return Response(
                {"status": "error", "error": {"message": "Les groupes système ne peuvent pas être supprimés."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if group.users.exists():
            return Response(
                {"status": "error", "error": {"message": "Le groupe contient encore des utilisateurs."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["get", "post"])
    def permissions(self, request, pk=None):
        group = self.get_object()
        if request.method == "GET":
            perms = group.permissions.all()
            serializer = PermissionSerializer(perms, many=True)
            return Response({"status": "success", "data": serializer.data})
        # POST: add permissions by codename list
        codenames = request.data.get("permissions", [])
        perms = Permission.objects.filter(codename__in=codenames)
        group.permissions.add(*perms)
        return Response({"status": "success"})

    @action(detail=True, methods=["get", "post"])
    def users(self, request, pk=None):
        group = self.get_object()
        if request.method == "GET":
            users = group.users.all()
            serializer = UserListSerializer(users, many=True)
            return Response({"status": "success", "data": serializer.data})
        # POST: add users by ID list
        user_ids = request.data.get("users", [])
        users = User.objects.filter(pk__in=user_ids)
        group.users.add(*users)
        return Response({"status": "success"})


class PermissionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = PermissionFilter
    search_fields = ["codename", "name"]

    @action(detail=False, methods=["get"])
    def by_module(self, request):
        """Permissions grouped by module then feature."""
        from accounts.constants import MODULE_LABELS, PERMISSION_REGISTRY

        result = {}
        for perm in Permission.objects.all():
            mod = perm.module
            if mod not in result:
                result[mod] = {"label": MODULE_LABELS.get(mod, mod), "features": {}}
            feat = perm.feature
            if feat not in result[mod]["features"]:
                feat_info = PERMISSION_REGISTRY.get(mod, {}).get(feat, {})
                result[mod]["features"][feat] = {
                    "label": feat_info.get("label", feat),
                    "permissions": [],
                }
            result[mod]["features"][feat]["permissions"].append(
                PermissionSerializer(perm).data
            )
        return Response({"status": "success", "data": result})


class AccessLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AccessLog.objects.select_related("user")
    serializer_class = AccessLogSerializer
    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "system"
    permission_feature = "audit_trail"
    filterset_class = AccessLogFilter
    ordering_fields = ["timestamp"]


# ── Helpers ─────────────────────────────────────────────────

def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
