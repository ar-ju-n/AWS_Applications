from django import forms
from .models_researcher import Researcher

class ResearcherProfileForm(forms.ModelForm):
    class Meta:
        model = Researcher
        fields = ['institution', 'specialization', 'research_interests', 'publications']
        widgets = {
            'institution': forms.TextInput(attrs={'class': 'form-control'}),
            'specialization': forms.TextInput(attrs={'class': 'form-control'}),
            'research_interests': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'publications': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'institution': 'Institution',
            'specialization': 'Specialization',
            'research_interests': 'Research Interests',
            'publications': 'Publications (Optional)',
        }
        help_texts = {
            'specialization': 'Comma-separated list of specializations (e.g., depression, anxiety, bipolar)',
        }
