from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from .models import CustomUser
from .forms import CustomUserCreationForm
from telepsych_sessions.models import Patient, Psychiatrist
from telepsych_sessions.forms_profile import PatientProfileForm, PsychiatristProfileForm, ResearcherProfileForm
from telepsych_sessions.models import Researcher
from django.utils import timezone
from django.db import transaction

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            # Redirect to appropriate dashboard based on role
            if user.role == CustomUser.Roles.PATIENT:
                return redirect('telepsych_sessions:patient_dashboard')
            elif user.role == CustomUser.Roles.PSYCHIATRIST:
                return redirect('telepsych_sessions:psychiatrist_dashboard')
            elif user.role == CustomUser.Roles.RESEARCHER:
                return redirect('telepsych_sessions:researcher_dashboard')
            else:
                return redirect('telepsych_sessions:index')
        else:
            messages.error(request, 'Invalid email or password')
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    return redirect('accounts:login')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                # Start a transaction to ensure both user and profile are created
                with transaction.atomic():
                    # Create the user first
                    user = form.save(commit=False)
                    user.save()

                    # Create appropriate profile based on role
                    if user.role == CustomUser.Roles.PATIENT:
                        Patient.objects.create(
                            user=user,
                            date_of_birth='2000-01-01'  # Default date, will be updated in profile completion
                        )
                    elif user.role == CustomUser.Roles.PSYCHIATRIST:
                        # Generate unique license number
                        unique_license = f"TEMP-{user.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
                        Psychiatrist.objects.create(
                            user=user,
                            specialization='',
                            license_number=unique_license,
                            availability=[],
                            bio=''
                        )
                    elif user.role == CustomUser.Roles.RESEARCHER:
                        # Create researcher profile with required fields
                        Researcher.objects.create(
                            user=user,
                            institution='To be updated',
                            research_interests='',
                            bio=''
                        )
                    else:
                        raise ValueError('Invalid user role')

                    # Log the user in
                    login(request, user)
                    messages.success(request, 'Registration successful! Please complete your profile.')
                    return redirect('telepsych_sessions:complete_profile')

            except Exception as e:
                # If anything goes wrong, add error message and return to form
                messages.error(request, f'Registration failed: {str(e)}')
                return redirect('accounts:register')
        else:
            # If form is invalid, print errors for debugging
            print('REGISTER FORM ERRORS:', form.errors)
    else:
        form = CustomUserCreationForm()
        # Exclude admin role from choices
        form.fields['role'].choices = [
            (CustomUser.Roles.PATIENT, 'Patient'),
            (CustomUser.Roles.PSYCHIATRIST, 'Psychiatrist'),
            (CustomUser.Roles.RESEARCHER, 'Researcher')
        ]
    return render(request, 'accounts/register.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.role in [CustomUser.Roles.PATIENT, CustomUser.Roles.PSYCHIATRIST])
def profile(request):
    user = request.user
    if user.role == CustomUser.Roles.PATIENT:
        profile = user.patient
    else:  # CustomUser.Roles.PSYCHIATRIST
        profile = user.psychiatrist
    return render(request, 'accounts/profile.html', {'profile': profile})

@login_required
@user_passes_test(lambda u: u.role in [CustomUser.Roles.PATIENT, CustomUser.Roles.PSYCHIATRIST])
def edit_profile(request):
    user = request.user
    if user.role == CustomUser.Roles.PATIENT:
        profile = user.patient
        form_class = PatientProfileForm
    else:  # CustomUser.Roles.PSYCHIATRIST
        profile = user.psychiatrist
        form_class = PsychiatristProfileForm

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully')
            return redirect('accounts:profile')
    else:
        form = form_class(instance=profile)
    
    return render(request, 'accounts/edit_profile.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match')
        else:
            request.user.set_password(new_password)
            request.user.save()
            messages.success(request, 'Password changed successfully')
            return redirect('accounts:profile')
    
    return render(request, 'accounts/change_password.html')

def reset_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = CustomUser.objects.get(email=email)
            # Generate reset token and send email
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Send reset email
            subject = 'Password Reset Request'
            message = render_to_string('accounts/password_reset_email.html', {
                'user': user,
                'uid': uid,
                'token': token,
                'domain': request.get_host(),
            })
            
            user.email_user(subject, message)
            messages.success(request, 'Password reset instructions have been sent to your email')
            return redirect('accounts:login')
        except CustomUser.DoesNotExist:
            messages.error(request, 'No account found with this email')
    
    return render(request, 'accounts/reset_password.html')

def reset_password_done(request):
    return render(request, 'accounts/reset_password_done.html')

def reset_password_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
        
        if default_token_generator.check_token(user, token):
            if request.method == 'POST':
                password1 = request.POST.get('password1')
                password2 = request.POST.get('password2')
                
                if password1 and password2 and password1 == password2:
                    user.set_password(password1)
                    user.save()
                    messages.success(request, 'Password has been reset successfully')
                    return redirect('accounts:login')
                else:
                    messages.error(request, 'Passwords do not match')
            
            return render(request, 'accounts/reset_password_confirm.html')
        else:
            messages.error(request, 'Password reset link is invalid or has expired')
            return redirect('accounts:reset_password')
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        messages.error(request, 'Invalid password reset link')
        return redirect('accounts:reset_password')

def reset_password_complete(request):
    return render(request, 'accounts/reset_password_complete.html')
