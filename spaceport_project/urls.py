from django.urls import include, path

urlpatterns = [path('api/', include('charter_app.urls'))]
