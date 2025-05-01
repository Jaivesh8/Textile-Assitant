from django.urls import path
from .views import ProcessInfoView

urlpatterns=[
    path('process-info/',ProcessInfoView.as_view(),name='process-info')
]
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]