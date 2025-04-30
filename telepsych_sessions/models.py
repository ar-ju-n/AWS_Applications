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
    emergency_contact = models.CharField(max_length=100, blank=True, help_text="Name and phone number of emergency contact")
    medical_history = models.TextField(blank=True, help_text="Any relevant medical history or conditions")

    def __str__(self):
        return self.user.email

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
