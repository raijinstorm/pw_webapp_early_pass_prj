from django.urls import include, path
urlpatterns = [path("accounts/", include("django.contrib.auth.urls")), path("", include("app.urls"))]
