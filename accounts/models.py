from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    class Roles(models.TextChoices):
        PATIENT = 'PATIENT', 'Patient'
        PSYCHIATRIST = 'PSYCHIATRIST', 'Psychiatrist'
        ADMIN = 'ADMIN', 'Admin'
        RESEARCHER = 'RESEARCHER', 'Researcher'

    name = models.CharField(max_length=100, blank=False, default="User")
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Roles.choices)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.email} ({self.role})"
