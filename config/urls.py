

from django.contrib import admin
from django.urls import path, include
from debug_toolbar.toolbar import debug_toolbar_urls


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/',include('rest_framework.urls')),
    path(r'auth/', include('djoser.urls')),
    path(r'auth/', include('djoser.urls.jwt')),
]+debug_toolbar_urls()


