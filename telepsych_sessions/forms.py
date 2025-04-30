from django import forms
from .models import Session, Patient, Psychiatrist, SessionReview, SessionMessage
from django.utils import timezone

class SessionBookingForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['psychiatrist', 'scheduled_time', 'notes']
        widgets = {
            'scheduled_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'notes': forms.Textarea(attrs={'rows': 3})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['scheduled_time'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['scheduled_time'].help_text = 'Select a time slot that works for you'
        self.fields['notes'].help_text = 'Optional: Add any specific concerns or topics you want to discuss'

    def clean_scheduled_time(self):
        scheduled_time = self.cleaned_data.get('scheduled_time')
        if scheduled_time <= timezone.now():
            raise forms.ValidationError('Please select a future time')
        return scheduled_time

    def clean(self):
        cleaned_data = super().clean()
        scheduled_time = cleaned_data.get('scheduled_time')
        psychiatrist = cleaned_data.get('psychiatrist')

        if scheduled_time and psychiatrist:
            # Only check for exact time match (no overlap logic)
            overlapping_sessions = Session.objects.filter(
                psychiatrist=psychiatrist,
                scheduled_time=scheduled_time
            ).exclude(status=Session.Status.CANCELLED)
            if overlapping_sessions.exists():
                raise forms.ValidationError(
                    'Selected time slot is not available for this psychiatrist'
                )

        return cleaned_data

class SessionReviewForm(forms.ModelForm):
    class Meta:
        model = SessionReview
        fields = ['rating', 'feedback']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, str(i)) for i in range(1, 6)]),
            'feedback': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your feedback...'}),
        }

class SessionMessageForm(forms.ModelForm):
    class Meta:
        model = SessionMessage
        fields = ['message', 'file']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Type your message...'}),
        }
