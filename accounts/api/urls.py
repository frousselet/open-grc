from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.api import views

router = DefaultRouter()
router.register("users", views.UserViewSet, basename="user")
router.register("groups", views.GroupViewSet, basename="group")
router.register("permissions", views.PermissionViewSet, basename="permission")
router.register("access-logs", views.AccessLogViewSet, basename="access-log")

urlpatterns = [
    # Auth endpoints
    path("auth/login/", views.LoginAPIView.as_view(), name="api-login"),
    path("auth/logout/", views.LogoutAPIView.as_view(), name="api-logout"),
    path("auth/me/", views.MeAPIView.as_view(), name="api-me"),
    path("auth/refresh/", views.TokenRefreshAPIView.as_view(), name="api-token-refresh"),

    # Resource endpoints
    path("", include(router.urls)),
]
