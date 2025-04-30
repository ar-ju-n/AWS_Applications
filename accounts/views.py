from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .models import CustomUser
from .forms import CustomUserCreationForm
from telepsych_sessions.models import Patient, Psychiatrist
from telepsych_sessions.forms_profile import PatientProfileForm, PsychiatristProfileForm
from django.utils import timezone

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create Patient or Psychiatrist profile
            if user.role == CustomUser.Roles.PATIENT:
                patient = Patient.objects.create(user=user, date_of_birth='2000-01-01')
                login(request, user)
                return redirect('telepsych_sessions:complete_profile')
            elif user.role == CustomUser.Roles.PSYCHIATRIST:
                # Ensure unique license_number for each psychiatrist
                unique_license = f"TEMP-{user.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
                psychiatrist = Psychiatrist.objects.create(user=user, specialization='', license_number=unique_license, availability=[], bio='')
                login(request, user)
                return redirect('telepsych_sessions:complete_profile')
        else:
            print('REGISTER FORM ERRORS:', form.errors)  # Debug: print errors to console
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})
