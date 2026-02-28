from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    # Authentication
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),

    # Profile
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("password/change/", views.PasswordChangeView.as_view(), name="password-change"),

    # Users
    path("users/", views.UserListView.as_view(), name="user-list"),
    path("users/create/", views.UserCreateView.as_view(), name="user-create"),
    path("users/<uuid:pk>/", views.UserDetailView.as_view(), name="user-detail"),
    path("users/<uuid:pk>/edit/", views.UserUpdateView.as_view(), name="user-update"),

    # Groups
    path("groups/", views.GroupListView.as_view(), name="group-list"),
    path("groups/create/", views.GroupCreateView.as_view(), name="group-create"),
    path("groups/<uuid:pk>/", views.GroupDetailView.as_view(), name="group-detail"),
    path("groups/<uuid:pk>/edit/", views.GroupUpdateView.as_view(), name="group-update"),
    path("groups/<uuid:pk>/permissions/", views.GroupPermissionsUpdateView.as_view(), name="group-permissions-update"),
    path("groups/<uuid:pk>/users/", views.GroupUsersUpdateView.as_view(), name="group-users-update"),
    path("groups/<uuid:pk>/scopes/", views.GroupScopesUpdateView.as_view(), name="group-scopes-update"),

    # Permissions
    path("permissions/", views.PermissionListView.as_view(), name="permission-list"),

    # Logs
    path("access-logs/", views.AccessLogListView.as_view(), name="access-log-list"),
    path("action-logs/", views.ActionLogListView.as_view(), name="action-log-list"),
]
