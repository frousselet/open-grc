from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"essential-assets", views.EssentialAssetViewSet)
router.register(r"support-assets", views.SupportAssetViewSet)
router.register(r"dependencies", views.AssetDependencyViewSet)
router.register(r"groups", views.AssetGroupViewSet)
router.register(r"suppliers", views.SupplierViewSet)

app_name = "assets-api"

urlpatterns = [
    path("", include(router.urls)),
]
