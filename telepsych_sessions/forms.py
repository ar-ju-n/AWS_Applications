from django import forms
from .models import Session, Patient, Psychiatrist, SessionReview, SessionMessage, PatientHealthRecord, PatientMedication, SessionSummary, ResearchStudy, ResearchSurvey, StudyParticipant
from django.utils import timezone

class SessionBookingForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['scheduled_time', 'duration', 'notes']
        widgets = {
            'scheduled_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any specific concerns or topics you\'d like to discuss?'}),
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

class SessionRescheduleForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['scheduled_time']
        widgets = {
            'scheduled_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class SessionReviewForm(forms.ModelForm):
    class Meta:
        model = SessionReview
        fields = ['rating', 'feedback']
        widgets = {
            'feedback': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Share your experience...'}),
        }

class SessionMessageForm(forms.ModelForm):
    class Meta:
        model = SessionMessage
        fields = ['message', 'file']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Type your message...'}),
        }

class HealthRecordForm(forms.ModelForm):
    class Meta:
        model = PatientHealthRecord
        fields = ['mood_rating', 'sleep_hours', 'medication_taken', 'notes', 'symptoms', 'triggers', 'coping_strategies']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'How are you feeling today?'}),
            'symptoms': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Any symptoms you\'re experiencing?'}),
            'triggers': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Any triggers you\'ve noticed?'}),
            'coping_strategies': forms.Textarea(attrs={'rows': 2, 'placeholder': 'What coping strategies have you used?'}),
        }

class MedicationForm(forms.ModelForm):
    class Meta:
        model = PatientMedication
        fields = ['name', 'dosage', 'frequency', 'start_date', 'end_date', 'notes']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Any side effects or notes?'}),
        }

class SessionSummaryForm(forms.ModelForm):
    class Meta:
        model = SessionSummary
        fields = ['key_points', 'treatment_plan', 'homework', 'next_steps']
        widgets = {
            'key_points': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Key points discussed in the session'}),
            'treatment_plan': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Current treatment plan'}),
            'homework': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Assignments or tasks for the patient'}),
            'next_steps': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Next steps and follow-up plan'}),
        }

class ResearchStudyForm(forms.ModelForm):
    class Meta:
        model = ResearchStudy
        fields = [
            'title', 'description', 'start_date', 'end_date',
            'target_participants', 'inclusion_criteria', 'exclusion_criteria'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'inclusion_criteria': forms.Textarea(attrs={'rows': 3}),
            'exclusion_criteria': forms.Textarea(attrs={'rows': 3}),
        }

class ResearchSurveyForm(forms.ModelForm):
    class Meta:
        model = ResearchSurvey
        fields = ['title', 'description', 'questions', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'questions': forms.Textarea(attrs={'rows': 10}),
        }

    def clean_questions(self):
        questions = self.cleaned_data.get('questions')
        try:
            # Validate that questions is valid JSON
            import json
            if isinstance(questions, str):
                questions = json.loads(questions)
            return questions
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format for questions")

class StudyParticipantForm(forms.ModelForm):
    class Meta:
        model = StudyParticipant
        fields = ['patient', 'consent_date', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'consent_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        study = kwargs.pop('study', None)
        super().__init__(*args, **kwargs)
        if study:
            used_patients = StudyParticipant.objects.filter(study=study).values_list('patient_id', flat=True)
            self.fields['patient'].queryset = Patient.objects.exclude(id__in=used_patients)
        else:
            self.fields['patient'].queryset = Patient.objects.all()