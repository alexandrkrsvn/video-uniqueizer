from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import index, job_detail, JobViewSet, count_videos, yadisk_check, yadisk_list, yadisk_count_videos, download_log

router = DefaultRouter()
router.register('api/jobs', JobViewSet, basename='job')

urlpatterns = [
    path('', index, name='index'),
    path('jobs/<str:pk>/', job_detail, name='job_detail'),
    path('jobs/<str:pk>/log', download_log, name='download_log'),
    path('api/count_videos', count_videos, name='count_videos'),
    path('api/yadisk/check', yadisk_check, name='yadisk_check'),
    path('api/yadisk/list', yadisk_list, name='yadisk_list'),
    path('api/yadisk/count_videos', yadisk_count_videos, name='yadisk_count_videos'),
]

urlpatterns += router.urls