from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import index, job_detail, JobViewSet, count_videos

router = DefaultRouter()
router.register('api/jobs', JobViewSet, basename='job')

urlpatterns = [
    path('', index, name='index'),
    path('jobs/<str:pk>/', job_detail, name='job_detail'), 
    path('api/count_videos', count_videos, name='count_videos'),
]

urlpatterns += router.urls