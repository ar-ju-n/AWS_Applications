import logging
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import Patient, Psychiatrist, Researcher
from accounts.models import CustomUser

logger = logging.getLogger(__name__)

class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Exclude certain paths from the middleware check
            excluded_paths = [
                '/accounts/profile/',
                '/accounts/logout/',
                '/admin/',
                '/static/',
                '/media/',
                '/accounts/',
                '/sessions/profile/',
                '/sessions/complete-profile/',
                '/sessions/psychiatrist/dashboard/',
            ]
            # Exclude all researcher studies URLs
            if request.path_info.startswith('/sessions/researcher/studies/'):
                return self.get_response(request)
            # Exclude all psychiatrist URLs
            if request.path_info.startswith('/sessions/psychiatrist/'):
                return self.get_response(request)
            # Check if current path is in excluded paths
            current_path = request.path_info
            if any(current_path.startswith(path) for path in excluded_paths):
                return self.get_response(request)

            try:
                # Check if user profile is complete based on role
                user = request.user
                profile_complete = False

                if user.role == CustomUser.Roles.PATIENT:
                    profile = Patient.objects.get(user=user)
                    profile_complete = bool(profile.date_of_birth and profile.phone_number)
                elif user.role == CustomUser.Roles.PSYCHIATRIST:
                    profile = Psychiatrist.objects.get(user=user)
                    profile_complete = bool(profile.license_number and profile.specialization)
                elif user.role == CustomUser.Roles.RESEARCHER:
                    profile = Researcher.objects.get(user=user)
                    logger.info(f"Researcher profile check: institution='{profile.institution}', research_interests='{getattr(profile, 'research_interests', None)}', bio='{getattr(profile, 'bio', None)}'")
                    profile_complete = bool(profile.institution and profile.research_interests)

                if not profile_complete:
                    messages.warning(
                        request,
                        'Please complete your profile before accessing other features.'
                    )
                    return redirect('telepsych_sessions:complete_profile')

            except (Patient.DoesNotExist, Psychiatrist.DoesNotExist, Researcher.DoesNotExist) as e:
                logger.error(f"Profile not found for user {request.user.email}: {str(e)}")
                messages.warning(
                    request,
                    'Please complete your profile before accessing other features.'
                )
                return redirect('telepsych_sessions:complete_profile')
            except Exception as e:
                logger.error(f"Error checking profile completion: {str(e)}")
                return self.get_response(request)

        return self.get_response(request) 