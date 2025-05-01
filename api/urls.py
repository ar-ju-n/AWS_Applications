from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SessionViewSet, PatientViewSet, ResearchStudyViewSet

router = DefaultRouter()
router.register(r'sessions', SessionViewSet)
router.register(r'patients', PatientViewSet)
router.register(r'research-studies', ResearchStudyViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
