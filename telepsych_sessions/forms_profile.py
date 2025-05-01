from django import forms
from .models import Patient, Psychiatrist, CustomUser, Researcher
import json

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['name', 'email']
        widgets = {
            'email': forms.EmailInput(attrs={'readonly': True})
        }

class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['phone_number', 'address', 'date_of_birth', 'gender', 'emergency_contact', 'medical_history']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'gender': forms.Select(choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]),
            'medical_history': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Any relevant medical history or conditions'}),
            'emergency_contact': forms.TextInput(attrs={'placeholder': 'Emergency contact person and phone'})
        }

class PsychiatristProfileForm(forms.ModelForm):
    availability_list = forms.CharField(
        label='Availability',
        required=False,
        widget=forms.Textarea(attrs={'placeholder': 'e.g. Monday 10:00-12:00\nWednesday 14:00-16:00', 'rows': 3})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate the textarea with a newline-separated string if availability is a list
        if self.instance and self.instance.availability:
            if isinstance(self.instance.availability, list):
                self.fields['availability_list'].initial = '\n'.join(self.instance.availability)
            elif isinstance(self.instance.availability, str):
                try:
                    avail = json.loads(self.instance.availability)
                    if isinstance(avail, list):
                        self.fields['availability_list'].initial = '\n'.join(avail)
                except Exception:
                    pass

    def clean_availability(self):
        # This method is now replaced by clean_availability_list
        return self.instance.availability

    def clean_availability_list(self):
        data = self.cleaned_data.get('availability_list', '').strip()
        if not data:
            return []
        # Split by lines and remove empty lines
        avail_list = [line.strip() for line in data.splitlines() if line.strip()]
        return avail_list

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.availability = self.cleaned_data.get('availability_list', [])
        if commit:
            instance.save()
        return instance

    class Meta:
        model = Psychiatrist
        fields = ['specialization', 'license_number', 'bio']

class ResearcherProfileForm(forms.ModelForm):
    class Meta:
        model = Researcher
        fields = ['institution', 'research_interests', 'bio']
        widgets = {
            'research_interests': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Your research interests and areas of expertise'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Your professional background and experience'})
        }
