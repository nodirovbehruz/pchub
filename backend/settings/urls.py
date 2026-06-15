from django.conf import settings
from django.contrib import admin
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView

admin.site.site_header = "🎮 PCHub Gaming Control Center"
admin.site.site_title = "PChub Admin"
admin.site.index_title = "Welcome to PCHub Gaming Dashboard"
admin.site.enable_nav_sidebar = True


API_PREFIX = "api"
DOCS_PREFIX = "docs"


@csrf_exempt
def health_check(request):
    """Health check endpoint for monitoring"""
    return JsonResponse({"status": "healthy", "service": "pchub", "version": "1.0.0"})


api_v1_urlpatterns = [
    path(f"{API_PREFIX}/v1/accounts/", include("apps.accounts.api.v1.urls")),
    path(f"{API_PREFIX}/v1/shops/", include("apps.shops.api.v1.urls")),
    path(f"{API_PREFIX}/v1/games/", include("apps.games.api.v1.urls")),
    path(f"{API_PREFIX}/v1/computers/", include("apps.computers.api.v1.urls")),
    path(f"{API_PREFIX}/v1/billing/", include("apps.billing.api.v1.urls")),
    path(f"{API_PREFIX}/v1/clubs/", include("apps.clubs.api.v1.urls")),
    path(f"{API_PREFIX}/v1/platform/", include("apps.clubs.api.v1.platform_urls")),
    path(f"{API_PREFIX}/v1/bookings/", include("apps.bookings.api.v1.urls")),
    path(f"{API_PREFIX}/v1/sessions/", include("apps.sessions_.api.v1.urls")),
    path(f"{API_PREFIX}/v1/loyalty/", include("apps.loyalty.api.v1.urls")),
    path(f"{API_PREFIX}/v1/content/", include("apps.content.api.v1.urls")),
    path(f"{API_PREFIX}/v1/integrations/", include("apps.integrations.api.v1.urls")),
]

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health"),
    path("graphql/", csrf_exempt(GraphQLView.as_view(graphiql=True))),
    *api_v1_urlpatterns,
]

if "SWAGGER" in settings.FEATURES:
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularRedocView,
        SpectacularSwaggerView,
    )

    doc_urlpatterns = [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/schema/swagger/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path(
            "api/schema/redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc",
        ),
    ]

    urlpatterns += doc_urlpatterns


if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns += [
            path("__debug__/", include(debug_toolbar.urls)),
        ]

    if "silk" in settings.INSTALLED_APPS:
        urlpatterns += [
            path("silk/", include("silk.urls", namespace="silk")),
        ]
