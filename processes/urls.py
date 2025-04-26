from django.urls import path
from .views import ProcessInfoView

urlpatterns=[
    path('process-info/',ProcessInfoView.as_view(),name='process-info')
]