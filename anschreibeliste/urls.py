"""
URL configuration for anschreibeliste project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView

class CustomLoginView(LoginView):    
    def get_form(self, form_class = None):
        form = super().get_form(form_class)
        form.fields['username'].widget.attrs['placeholder'] = ' '
        form.fields['password'].widget.attrs['placeholder'] = ' '
        return form

urlpatterns = [
	path('admin/action-forms/', include('django_admin_action_forms.urls')),
    path('admin/', admin.site.urls),
    path("", include("ledger.urls")),
    path("wiki/", include("wiki.urls")),
    path("login/", CustomLoginView.as_view(), name='login'),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("recipes/", include("blackbook.urls")),
]

# Static file serving during development
if settings.DEBUG:
	urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
