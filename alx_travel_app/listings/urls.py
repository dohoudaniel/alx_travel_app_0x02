# listings/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ListingViewSet, BookingViewSet

# Swagger / OpenAPI imports (drf_yasg). If you prefer drf-spectacular, swap accordingly.
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

router = DefaultRouter()
router.register(r'listings', ListingViewSet, basename='listing')
router.register(r'bookings', BookingViewSet, basename='booking')

schema_view = get_schema_view(
   openapi.Info(
      title="ALX Travel App API",
      default_version='v1',
      description="API for Listings and Bookings (alx_travel_app_0x01)",
      contact=openapi.Contact(email="dev@example.com"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('api/', include(router.urls)),
    # Swagger/OpenAPI endpoints:
    path('api/swagger<str:format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

