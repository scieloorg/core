from django.urls import path
from .views import download_csv

app_name = 'home'

urlpatterns = [
    path('download-csv/', download_csv, name='download-csv'),
]