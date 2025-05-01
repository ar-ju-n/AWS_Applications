from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django_xray.middleware import XRayMiddleware
from telepsych_sessions.models import Session, Patient, ResearchStudy
from .serializers import SessionSerializer, PatientSerializer, ResearchStudySerializer

class SessionViewSet(viewsets.ModelViewSet):
    """API endpoint for managing sessions."""
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming sessions for the current user."""
        if request.user.role == 'PATIENT':
            sessions = Session.objects.filter(
                patient__user=request.user,
                scheduled_time__gt=timezone.now()
            )
        elif request.user.role == 'PSYCHIATRIST':
            sessions = Session.objects.filter(
                psychiatrist__user=request.user,
                scheduled_time__gt=timezone.now()
            )
        return Response(self.serializer_class(sessions, many=True).data)

class PatientViewSet(viewsets.ModelViewSet):
    """API endpoint for managing patients."""
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'PATIENT':
            return Patient.objects.filter(user=self.request.user)
        return Patient.objects.all()

class ResearchStudyViewSet(viewsets.ModelViewSet):
    """API endpoint for managing research studies."""
    queryset = ResearchStudy.objects.all()
    serializer_class = ResearchStudySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'RESEARCHER':
            return ResearchStudy.objects.filter(researcher__user=self.request.user)
        return ResearchStudy.objects.all()

    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """Get all participants for a specific study."""
        study = self.get_object()
        participants = study.participants.all()
        return Response(PatientSerializer(participants, many=True).data)
