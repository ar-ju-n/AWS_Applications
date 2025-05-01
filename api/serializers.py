from rest_framework import serializers
from telepsych_sessions.models import Session, Patient, ResearchStudy

class SessionSerializer(serializers.ModelSerializer):
    """Serializer for Session model."""
    class Meta:
        model = Session
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class PatientSerializer(serializers.ModelSerializer):
    """Serializer for Patient model."""
    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class ResearchStudySerializer(serializers.ModelSerializer):
    """Serializer for ResearchStudy model."""
    class Meta:
        model = ResearchStudy
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
