from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Researcher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='researcher_profile')
    institution = models.CharField(max_length=200)
    specialization = models.CharField(max_length=200)
    research_interests = models.TextField()
    publications = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Researcher: {self.user.email}"

    class Meta:
        verbose_name = 'Researcher'
        verbose_name_plural = 'Researchers'

    def get_sessions_access(self):
        """Get sessions that this researcher has access to based on their specialization"""
        return Session.objects.filter(
            psychiatrist__specialization__in=self.specialization.split(',')
        )
