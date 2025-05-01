from django.db import models
from django.utils import timezone
from datetime import timedelta
from accounts.models import CustomUser
from .models_notification import Notification

app_name = 'telepsych_sessions'

class Patient(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': CustomUser.Roles.PATIENT}
    )
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True, help_text="Name and phone number of emergency contact")
    medical_history = models.TextField(blank=True, help_text="Any relevant medical history or conditions")
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    emergency_contact_email = models.EmailField(blank=True)

    def __str__(self):
        return self.user.email

class PatientHealthRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='health_records')
    date = models.DateField(default=timezone.now)
    mood_rating = models.IntegerField(choices=[(i, i) for i in range(1, 11)], help_text="1-10 scale")
    sleep_hours = models.FloatField(help_text="Hours of sleep")
    medication_taken = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    symptoms = models.TextField(blank=True, help_text="Any symptoms experienced")
    triggers = models.TextField(blank=True, help_text="Potential triggers for mood changes")
    coping_strategies = models.TextField(blank=True, help_text="Coping strategies used")

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.patient.user.email} - {self.date}"

class PatientMedication(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medications')
    name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50)
    frequency = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.patient.user.email} - {self.name}"

class SessionSummary(models.Model):
    session = models.OneToOneField('Session', on_delete=models.CASCADE, related_name='summary')
    key_points = models.TextField()
    treatment_plan = models.TextField()
    homework = models.TextField(blank=True)
    next_steps = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Summary for Session {self.session.id}"

class Psychiatrist(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': CustomUser.Roles.PSYCHIATRIST}
    )
    specialization = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    availability = models.JSONField(default=list)  # List of available time slots
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.user.email

class Researcher(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': CustomUser.Roles.RESEARCHER}
    )
    institution = models.CharField(max_length=200)
    research_interests = models.TextField(blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.user.email

class Session(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    psychiatrist = models.ForeignKey(Psychiatrist, on_delete=models.CASCADE)
    scheduled_time = models.DateTimeField()
    duration = models.DurationField(default=timedelta(hours=1))  # Default 1 hour
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    notes = models.TextField(blank=True)
    video_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_upcoming(self):
        return self.scheduled_time > timezone.now()

    def __str__(self):
        return f"{self.patient} with {self.psychiatrist} on {self.scheduled_time}"

    class Meta:
        ordering = ['-scheduled_time']

class SessionReview(models.Model):
    session = models.OneToOneField('Session', on_delete=models.CASCADE, related_name='review')
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for Session {self.session.id} by {self.patient.user.email}"

class SessionMessage(models.Model):
    session = models.ForeignKey('Session', on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    message = models.TextField(blank=True)
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message by {self.sender.email} in Session {self.session.id}"

class SessionTypingStatus(models.Model):
    session = models.ForeignKey('Session', on_delete=models.CASCADE, related_name='typing_statuses')
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    is_typing = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('session', 'user')

    def __str__(self):
        return f"{self.user.email} typing in Session {self.session.id}: {self.is_typing}"

class ResearchStudy(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    title = models.CharField(max_length=200)
    description = models.TextField()
    researcher = models.ForeignKey(Researcher, on_delete=models.CASCADE, related_name='studies')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    target_participants = models.IntegerField()
    current_participants = models.IntegerField(default=0)
    inclusion_criteria = models.TextField()
    exclusion_criteria = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.researcher.user.email}"

    class Meta:
        verbose_name_plural = 'Research Studies'
        ordering = ['-created_at']

class StudyParticipant(models.Model):
    study = models.ForeignKey(ResearchStudy, on_delete=models.CASCADE, related_name='participants')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='studies')
    joined_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVE', 'Active'),
            ('COMPLETED', 'Completed'),
            ('WITHDRAWN', 'Withdrawn')
        ],
        default='ACTIVE'
    )
    notes = models.TextField(blank=True)
    consent_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('study', 'patient')
        ordering = ['-joined_at']

class ResearchData(models.Model):
    study = models.ForeignKey(ResearchStudy, on_delete=models.CASCADE, related_name='data')
    participant = models.ForeignKey(StudyParticipant, on_delete=models.CASCADE, related_name='data')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='research_data')
    data_type = models.CharField(max_length=50)  # e.g., 'mood_rating', 'sleep_hours', etc.
    value = models.JSONField()  # Store various types of data
    collected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-collected_at']

class ResearchSurvey(models.Model):
    study = models.ForeignKey(ResearchStudy, on_delete=models.CASCADE, related_name='surveys')
    title = models.CharField(max_length=200)
    description = models.TextField()
    questions = models.JSONField()  # Store survey questions and options
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.study.title}"

class SurveyResponse(models.Model):
    survey = models.ForeignKey(ResearchSurvey, on_delete=models.CASCADE, related_name='responses')
    participant = models.ForeignKey(StudyParticipant, on_delete=models.CASCADE, related_name='survey_responses')
    answers = models.JSONField()  # Store participant's answers
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']
