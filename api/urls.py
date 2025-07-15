from django.urls import path
from . import views

urlpatterns = [
    path('generate_level_content/', views.GenerateLevelContentView.as_view(), name='generate_level_content'),
    path('bulk_generate/', views.BulkGenerateView.as_view(), name='bulk_generate'),
    path('bulk_generate_with_content/', views.BulkGenerateWithContentView.as_view(), name='bulk_generate_with_content'),
]
