from django.urls import path
from .views import clean_database_redis, confirm_clean_database_redis


urlpatterns = [
    path('confirm-clean-database-redis/', confirm_clean_database_redis, name='confirm_clean_database_redis'),
    path('clean-database-redis/', clean_database_redis, name='clean_database_redis'),
]