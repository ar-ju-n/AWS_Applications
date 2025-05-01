import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse, Http404
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import PermissionDenied
import os
from django.conf import settings
from .models import Session, Patient, Psychiatrist, Researcher, SessionMessage, SessionTypingStatus, ResearchStudy, StudyParticipant, ResearchSurvey, SurveyResponse
from accounts.models import CustomUser
from .forms import SessionBookingForm, SessionReviewForm, SessionMessageForm, ResearchStudyForm, ResearchSurveyForm, StudyParticipantForm
from .forms_profile import PatientProfileForm, PsychiatristProfileForm, ResearcherProfileForm, UserProfileForm
from .models_notification import Notification
import uuid
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from reportlab.pdfgen import canvas
from django.forms import Form, CharField

logger = logging.getLogger(__name__)

@login_required
def serve_chat_file(request, filename):
    """Serve chat attachment files securely."""
    try:
        # Get the session ID from the filename (first part before underscore)
        session_id = filename.split('_')[0]
        session = get_object_or_404(Session, id=session_id)
        
        # Check if user has access to this session
        if request.user.role == CustomUser.Roles.PATIENT and session.patient.user != request.user:
            raise PermissionDenied("You don't have permission to access this file")
        elif request.user.role == CustomUser.Roles.PSYCHIATRIST and session.psychiatrist.user != request.user:
            raise PermissionDenied("You don't have permission to access this file")
            
        # Get the full path to the file
        file_path = os.path.join(settings.MEDIA_ROOT, 'chat_files', filename)
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise Http404("File not found")
            
        # Determine content type based on file extension
        content_type = 'application/octet-stream'
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            content_type = 'image/jpeg' if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg') else 'image/png'
        elif filename.lower().endswith(('.pdf')):
            content_type = 'application/pdf'
        elif filename.lower().endswith(('.doc', '.docx')):
            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        
        # Serve the file
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
    except PermissionDenied as e:
        messages.error(request, str(e))
        return redirect('telepsych_sessions:session_chat', session_id=session_id)
    except Exception as e:
        logger.error(f"Error serving chat file: {str(e)}")
        raise Http404("File access error")

@login_required
def home(request):
    if request.user.role == CustomUser.Roles.PATIENT:
        return redirect('patient_dashboard')
    elif request.user.role == CustomUser.Roles.PSYCHIATRIST:
        return redirect('psychiatrist_dashboard')
    return redirect('admin:index')

def index(request):
    """Public home page"""
    return render(request, 'index.html')

def about(request):
    """About us page"""
    return render(request, 'about.html')

def contact(request):
    """Contact page"""
    return render(request, 'contact.html')

@login_required
def patient_dashboard(request):
    patient = get_object_or_404(Patient, user=request.user)
    status_filter = request.GET.get('status', '')
    
    # Get all sessions for this patient
    sessions = Session.objects.filter(patient=patient)
    
    # Apply filtering
    if status_filter and status_filter in dict(Session.Status.choices):
        sessions = sessions.filter(status=status_filter)
    
    # Get sessions by psychiatrist
    psychiatrist_filter = request.GET.get('psychiatrist', '')
    if psychiatrist_filter:
        try:
            psychiatrist = Psychiatrist.objects.get(user__email=psychiatrist_filter)
            sessions = sessions.filter(psychiatrist=psychiatrist)
        except Psychiatrist.DoesNotExist:
            messages.warning(request, 'Psychiatrist not found')
    
    unread_count = request.user.notifications.filter(is_read=False).count()
    unread_chat_count = get_unread_chat_count(request.user)
    notifications = request.user.notifications.order_by('-created_at')[:10]
    
    # Get all available psychiatrists for the dropdown
    available_psychiatrists = Psychiatrist.objects.all()
    
    # Show all active surveys from all active studies to every patient
    public_surveys = []
    active_studies = ResearchStudy.objects.filter(status=ResearchStudy.Status.ACTIVE)
    for study in active_studies:
        available_surveys = []
        for survey in study.surveys.filter(is_active=True):
            # Check if patient has already completed this survey
            sp = StudyParticipant.objects.filter(study=study, patient=patient).first()
            if sp and SurveyResponse.objects.filter(survey=survey, participant=sp).exists():
                continue
            available_surveys.append(survey)
        if available_surveys:
            public_surveys.append({'study': study, 'surveys': available_surveys})
    
    # Find the first available survey for direct link
    first_survey_link = None
    for item in public_surveys:
        for survey in item['surveys']:
            first_survey_link = {
                'study_id': item['study'].id,
                'survey_id': survey.id,
                'title': survey.title,
            }
            break
        if first_survey_link:
            break
    
    all_active_studies = ResearchStudy.objects.filter(status=ResearchStudy.Status.ACTIVE)
    all_active_surveys = ResearchSurvey.objects.filter(is_active=True)
    
    # Filter all_active_surveys to only those not completed by this patient
    filtered_active_surveys = []
    if hasattr(request.user, 'patient'):
        patient = request.user.patient
        for survey in all_active_surveys:
            sp = StudyParticipant.objects.filter(study=survey.study, patient=patient).first()
            if sp and SurveyResponse.objects.filter(survey=survey, participant=sp).exists():
                continue
            filtered_active_surveys.append(survey)
    else:
        filtered_active_surveys = list(all_active_surveys)
    
    return render(request, 'patient_dashboard.html', {
        'sessions': sessions.order_by('-scheduled_time'),
        'status_filter': status_filter,
        'psychiatrist_filter': psychiatrist_filter,
        'available_psychiatrists': available_psychiatrists,
        'unread_count': unread_count,
        'unread_chat_count': unread_chat_count,
        'notifications': notifications,
        'public_surveys': public_surveys,
        'first_survey_link': first_survey_link,
        'all_active_studies': all_active_studies,
        'all_active_surveys': filtered_active_surveys,
    })

@login_required
def book_session(request):
    if request.user.role != CustomUser.Roles.PATIENT:
        return redirect('home')
    
    patient = get_object_or_404(Patient, user=request.user)
    available_psychiatrists = Psychiatrist.objects.all()
    
    if request.method == 'POST':
        form = SessionBookingForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.patient = patient
            session.status = Session.Status.PENDING
            session.save()
            messages.success(request, 'Session booked successfully!')
            # In-app notification for psychiatrist
            Notification.objects.create(
                user=session.psychiatrist.user,
                message=f'New session booked by {request.user.email}.'
            )
            return redirect('telepsych_sessions:patient_dashboard')
        
        import sys
        print('BOOK SESSION FORM ERRORS:', form.errors, file=sys.stderr)
        return JsonResponse({'error': form.errors.as_json()}, status=400)
    
    form = SessionBookingForm()
    return render(request, 'book_session.html', {
        'form': form,
        'available_psychiatrists': available_psychiatrists
    })

@login_required
def psychiatrist_dashboard(request):
    psychiatrist = get_object_or_404(Psychiatrist, user=request.user)
    status_filter = request.GET.get('status', '')
    sessions = Session.objects.filter(psychiatrist=psychiatrist)
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    unread_count = request.user.notifications.filter(is_read=False).count()
    unread_chat_count = get_unread_chat_count(request.user)
    notifications = request.user.notifications.order_by('-created_at')[:10]

    # Separate pending sessions for template context
    pending_sessions = sessions.filter(status=Session.Status.PENDING).order_by('-scheduled_time')

    return render(request, 'psychiatrist_dashboard.html', {
        'sessions': sessions.order_by('-scheduled_time'),
        'pending_sessions': pending_sessions,
        'status_filter': status_filter,
        'unread_count': unread_count,
        'unread_chat_count': unread_chat_count,
        'notifications': notifications,
    })

@login_required
def manage_sessions(request):
    if request.user.role != CustomUser.Roles.PSYCHIATRIST:
        return redirect('home')
    try:
        
        psychiatrist = Psychiatrist.objects.get(user=request.user)
    except Psychiatrist.DoesNotExist:
        # Optionally, redirect to complete profile if needed
        return redirect('telepsych_sessions:complete_profile')
    sessions = Session.objects.filter(
        psychiatrist=psychiatrist
    ).select_related('patient', 'psychiatrist').order_by('-scheduled_time')
    
    return render(request, 'manage_sessions.html', {
        'psychiatrist': psychiatrist,
        'sessions': sessions
    })

@login_required
def accept_session(request, session_id):
    if request.user.role != CustomUser.Roles.PSYCHIATRIST:
        return redirect('telepsych_sessions:manage_sessions')
    session = get_object_or_404(Session, id=session_id)
    if session.psychiatrist.user != request.user:
        return redirect('telepsych_sessions:manage_sessions')
    session.status = Session.Status.ACCEPTED
    # Generate Jitsi Meet link if not set
    if not session.video_link:
        room_name = f"telepsych-{session.id}-{uuid.uuid4().hex[:8]}"
        session.video_link = f"https://meet.jit.si/{room_name}"
    session.save()
    messages.success(request, 'Session accepted!')
    # Notify patient
    Notification.objects.create(
        user=session.patient.user,
        message=f'Your session on {session.scheduled_time} was accepted.'
    )
    return redirect('telepsych_sessions:manage_sessions')

@login_required
def reject_session(request, session_id):
    if request.user.role != CustomUser.Roles.PSYCHIATRIST:
        return redirect('telepsych_sessions:manage_sessions')
    session = get_object_or_404(Session, id=session_id)
    if session.psychiatrist.user != request.user:
        return redirect('telepsych_sessions:manage_sessions')
    session.status = Session.Status.REJECTED
    session.save()
    messages.info(request, 'Session rejected.')
    # Notify patient
    Notification.objects.create(
        user=session.patient.user,
        message=f'Your session on {session.scheduled_time} was rejected.'
    )
    return redirect('telepsych_sessions:manage_sessions')

@login_required
def cancel_session(request, session_id):
    if request.user.role not in [CustomUser.Roles.PATIENT, CustomUser.Roles.PSYCHIATRIST]:
        return redirect('telepsych_sessions:manage_sessions')
    session = get_object_or_404(Session, id=session_id)
    # Check if user is authorized to cancel this session
    if (request.user.role == CustomUser.Roles.PATIENT and 
        session.patient.user != request.user) or \
       (request.user.role == CustomUser.Roles.PSYCHIATRIST and 
        session.psychiatrist.user != request.user):
        return redirect('telepsych_sessions:manage_sessions')
    session.status = Session.Status.CANCELLED
    session.save()
    messages.warning(request, 'Session cancelled.')
    # Notify both users
    Notification.objects.create(
        user=session.patient.user,
        message=f'Your session on {session.scheduled_time} was cancelled.'
    )
    Notification.objects.create(
        user=session.psychiatrist.user,
        message=f'A session with {session.patient.user.email} was cancelled.'
    )
    return redirect('telepsych_sessions:manage_sessions')

@login_required
def complete_profile(request):
    user = request.user
    
    try:
        # Get or create the appropriate profile based on user role
        if user.role == CustomUser.Roles.PATIENT:
            profile, created = Patient.objects.get_or_create(user=user)
            form_class = PatientProfileForm
            success_url = 'telepsych_sessions:patient_dashboard'
        elif user.role == CustomUser.Roles.PSYCHIATRIST:
            profile, created = Psychiatrist.objects.get_or_create(user=user)
            form_class = PsychiatristProfileForm
            success_url = 'telepsych_sessions:psychiatrist_dashboard'
        elif user.role == CustomUser.Roles.RESEARCHER:
            profile, created = Researcher.objects.get_or_create(user=user)
            form_class = ResearcherProfileForm
            success_url = 'telepsych_sessions:researcher_dashboard'
        else:
            messages.error(request, 'Invalid user role')
            return redirect('telepsych_sessions:index')

        if request.method == 'POST':
            form = form_class(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile completed successfully!')
                return redirect(success_url)
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = form_class(instance=profile)

        return render(request, 'complete_profile.html', {
            'form': form,
            'role': user.get_role_display()
        })

    except Exception as e:
        messages.error(request, f'Error creating profile: {str(e)}')
        return redirect('telepsych_sessions:index')

@login_required
def edit_profile(request):
    user = request.user
    try:
        if user.role == CustomUser.Roles.PATIENT:
            profile, created = Patient.objects.get_or_create(user=user)
            form_class = PatientProfileForm
            success_url = 'telepsych_sessions:patient_dashboard'
        elif user.role == CustomUser.Roles.PSYCHIATRIST:
            profile, created = Psychiatrist.objects.get_or_create(user=user)
            form_class = PsychiatristProfileForm
            success_url = 'telepsych_sessions:psychiatrist_dashboard'
        elif user.role == CustomUser.Roles.RESEARCHER:
            profile, created = Researcher.objects.get_or_create(user=user)
            form_class = ResearcherProfileForm
            success_url = 'telepsych_sessions:researcher_dashboard'
        else:
            messages.error(request, 'Invalid user role')
            return redirect('telepsych_sessions:index')

        if request.method == 'POST':
            user_form = UserProfileForm(request.POST, instance=user)
            profile_form = form_class(request.POST, request.FILES, instance=profile)
            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                messages.success(request, 'Profile updated successfully')
                return redirect(success_url)
        else:
            user_form = UserProfileForm(instance=user)
            profile_form = form_class(instance=profile)
        
        return render(request, 'accounts/edit_profile.html', {'user_form': user_form, 'profile_form': profile_form, 'user': user})
    except Exception as e:
        messages.error(request, f'Error accessing profile: {str(e)}')
        return redirect('telepsych_sessions:index')

@login_required
@user_passes_test(lambda u: u.role == CustomUser.Roles.RESEARCHER)
def researcher_dashboard(request):
    try:
        researcher = Researcher.objects.get(user=request.user)
    except Researcher.DoesNotExist:
        messages.info(request, 'Please complete your researcher profile first.')
        return redirect('telepsych_sessions:complete_profile')
    
    # Get all sessions for research purposes
    sessions = Session.objects.all().order_by('-scheduled_time')[:10]
    
    context = {
        'researcher': researcher,
        'recent_sessions': sessions,
        'research_interests': researcher.research_interests,
        'institution': researcher.institution,
        'bio': researcher.bio
    }
    return render(request, 'telepsych_sessions/researcher_dashboard.html', context)

@login_required
def submit_review(request, session_id):
    session = get_object_or_404(Session, id=session_id, patient__user=request.user, status=Session.Status.COMPLETED)
    if hasattr(session, 'review'):
        messages.info(request, 'You have already submitted a review for this session.')
        return redirect('telepsych_sessions:patient_dashboard')
    if request.method == 'POST':
        form = SessionReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.session = session
            review.patient = session.patient
            review.save()
            messages.success(request, 'Thank you for your feedback!')
            # Notify psychiatrist when review is submitted
            Notification.objects.create(
                user=session.psychiatrist.user,
                message=f'New review received for session on {session.scheduled_time}.'
            )
            return redirect('telepsych_sessions:patient_dashboard')
    else:
        form = SessionReviewForm()
    return render(request, 'submit_review.html', {'form': form, 'session': session})

def get_unread_chat_count(user):
    from .models import SessionMessage, Psychiatrist, Patient
    # If user is a psychiatrist, find their Psychiatrist profile and count messages
    try:
        psychiatrist = Psychiatrist.objects.get(user=user)
        return SessionMessage.objects.filter(session__psychiatrist=psychiatrist, is_read=False).exclude(sender=user).count()
    except Psychiatrist.DoesNotExist:
        pass
    # If user is a patient, find their Patient profile and count messages
    try:
        patient = Patient.objects.get(user=user)
        return SessionMessage.objects.filter(session__patient=patient, is_read=False).exclude(sender=user).count()
    except Patient.DoesNotExist:
        pass
    return 0

@require_GET
def session_chat_ajax(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if not (hasattr(session, 'patient') and session.patient.user == request.user) and not (hasattr(session, 'psychiatrist') and session.psychiatrist.user == request.user):
        return HttpResponse(status=403)
    messages_qs = session.messages.select_related('sender').all()
    # Mark unread messages from the other user as read
    messages_qs.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    html = render_to_string('session_chat_messages.html', {'messages': messages_qs, 'user': request.user})
    return HttpResponse(html)

@login_required
def session_chat(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if not (hasattr(session, 'patient') and session.patient.user == request.user) and not (hasattr(session, 'psychiatrist') and session.psychiatrist.user == request.user):
        return redirect('telepsych_sessions:home')
    messages_qs = session.messages.select_related('sender').all()
    # Mark unread messages from the other user as read
    messages_qs.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    if request.method == 'POST':
        form = SessionMessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.session = session
            msg.sender = request.user
            msg.save()
            # Notify recipient of new unread chat message
            recipient = session.patient.user if request.user == session.psychiatrist.user else session.psychiatrist.user
            Notification.objects.create(
                user=recipient,
                message=f'New chat message in your session on {session.scheduled_time}.'
            )
            return redirect('telepsych_sessions:session_chat', session_id=session.id)
    else:
        form = SessionMessageForm()
    if request.GET.get('ajax') == '1':
        html = render_to_string('session_chat_messages.html', {'messages': messages_qs, 'user': request.user})
        return HttpResponse(html)
    return render(request, 'session_chat.html', {'session': session, 'messages': messages_qs, 'form': form})

@login_required
def edit_message(request, message_id):
    msg = get_object_or_404(SessionMessage, id=message_id, sender=request.user)
    if request.method == 'POST':
        form = SessionMessageForm(request.POST, request.FILES, instance=msg)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
    else:
        form = SessionMessageForm(instance=msg)
    return render(request, 'edit_message_form.html', {'form': form, 'message_id': msg.id})

@login_required
def delete_message(request, message_id):
    msg = get_object_or_404(SessionMessage, id=message_id, sender=request.user)
    if request.method == 'POST':
        msg.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

@login_required
def search_chat(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    q = request.GET.get('q', '')
    messages_qs = session.messages.select_related('sender').all()
    if q:
        messages_qs = messages_qs.filter(message__icontains=q)
    html = render_to_string('session_chat_messages.html', {'messages': messages_qs, 'user': request.user})
    return JsonResponse({'html': html})

@csrf_exempt
@login_required
def set_typing_status(request, session_id):
    if request.method == 'POST':
        session = get_object_or_404(Session, id=session_id)
        is_typing = request.POST.get('is_typing') == '1'
        obj, created = SessionTypingStatus.objects.get_or_create(session=session, user=request.user)
        obj.is_typing = is_typing
        obj.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

@require_GET
def get_typing_status(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    # Show typing status of the other user
    if hasattr(session, 'patient') and session.patient.user == request.user:
        other_user = session.psychiatrist.user
    else:
        other_user = session.patient.user
    typing = SessionTypingStatus.objects.filter(session=session, user=other_user, is_typing=True).exists()
    return JsonResponse({'typing': typing})

@login_required
def chats_list(request):
    user = request.user
    sessions = []
    # For psychiatrists, list sessions where they are the psychiatrist
    if hasattr(user, 'psychiatrist'):
        sessions = Session.objects.filter(psychiatrist__user=user).select_related('patient', 'psychiatrist').order_by('-scheduled_time')
    # For patients, list sessions where they are the patient
    elif hasattr(user, 'patient'):
        sessions = Session.objects.filter(patient__user=user).select_related('patient', 'psychiatrist').order_by('-scheduled_time')
    return render(request, 'chats_list.html', {'sessions': sessions})

@login_required
def view_profile(request):
    user = request.user
    context = {
        'user': user,
        'profile': None
    }
    
    if user.role == 'PSYCHIATRIST':
        context['profile'] = user.psychiatrist if hasattr(user, 'psychiatrist') else None
    elif user.role == 'PATIENT':
        context['profile'] = user.patient if hasattr(user, 'patient') else None
    
    return render(request, 'view_profile.html', context)

@login_required
def notifications_history(request):
    notifications = request.user.notifications.order_by('-created_at')
    return render(request, 'notifications_history.html', {'notifications': notifications})

@login_required
def patient_health_records(request):
    patient = get_object_or_404(Patient, user=request.user)
    health_records = patient.health_records.all().order_by('-date')
    
    if request.method == 'POST':
        form = HealthRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.patient = patient
            record.save()
            messages.success(request, 'Health record added successfully')
            return redirect('telepsych_sessions:patient_health_records')
    else:
        form = HealthRecordForm()
    
    return render(request, 'patient_health_records.html', {
        'health_records': health_records,
        'form': form
    })

@login_required
def patient_medications(request):
    patient = get_object_or_404(Patient, user=request.user)
    medications = patient.medications.all().order_by('-start_date')
    
    if request.method == 'POST':
        form = MedicationForm(request.POST)
        if form.is_valid():
            medication = form.save(commit=False)
            medication.patient = patient
            medication.save()
            messages.success(request, 'Medication added successfully')
            return redirect('telepsych_sessions:patient_medications')
    else:
        form = MedicationForm()
    
    return render(request, 'patient_medications.html', {
        'medications': medications,
        'form': form
    })

@login_required
def reschedule_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if session.patient.user != request.user and session.psychiatrist.user != request.user:
        raise PermissionDenied("You don't have permission to reschedule this session")
    
    if request.method == 'POST':
        form = SessionRescheduleForm(request.POST, instance=session)
        if form.is_valid():
            session = form.save()
            messages.success(request, 'Session rescheduled successfully')
            # Notify both parties
            Notification.objects.create(
                user=session.patient.user,
                message=f'Your session has been rescheduled to {session.scheduled_time}'
            )
            Notification.objects.create(
                user=session.psychiatrist.user,
                message=f'Session with {session.patient.user.email} has been rescheduled to {session.scheduled_time}'
            )
            return redirect('telepsych_sessions:session_detail', session_id=session.id)
    else:
        form = SessionRescheduleForm(instance=session)
    
    return render(request, 'reschedule_session.html', {
        'form': form,
        'session': session
    })

@login_required
def session_detail(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if session.patient.user != request.user and session.psychiatrist.user != request.user:
        raise PermissionDenied("You don't have permission to view this session")
    
    try:
        summary = session.summary
    except SessionSummary.DoesNotExist:
        summary = None
    
    return render(request, 'session_detail.html', {
        'session': session,
        'summary': summary
    })

@login_required
def create_session_summary(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if session.psychiatrist.user != request.user:
        raise PermissionDenied("Only the psychiatrist can create session summaries")
    
    if request.method == 'POST':
        form = SessionSummaryForm(request.POST)
        if form.is_valid():
            summary = form.save(commit=False)
            summary.session = session
            summary.save()
            messages.success(request, 'Session summary created successfully')
            # Notify patient
            Notification.objects.create(
                user=session.patient.user,
                message=f'New session summary available for your session on {session.scheduled_time}'
            )
            return redirect('telepsych_sessions:session_detail', session_id=session.id)
    else:
        form = SessionSummaryForm()
    
    return render(request, 'create_session_summary.html', {
        'form': form,
        'session': session
    })

@login_required
def download_session_summary(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if session.patient.user != request.user and session.psychiatrist.user != request.user:
        raise PermissionDenied("You don't have permission to download this summary")
    
    try:
        summary = session.summary
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="session_{session_id}_summary.pdf"'
        
        # Generate PDF content
        p = canvas.Canvas(response)
        p.drawString(100, 800, f"Session Summary - {session.scheduled_time}")
        p.drawString(100, 780, f"Patient: {session.patient.user.email}")
        p.drawString(100, 760, f"Psychiatrist: {session.psychiatrist.user.email}")
        p.drawString(100, 740, "Key Points:")
        p.drawString(100, 720, summary.key_points)
        p.drawString(100, 700, "Treatment Plan:")
        p.drawString(100, 680, summary.treatment_plan)
        p.drawString(100, 660, "Homework:")
        p.drawString(100, 640, summary.homework)
        p.drawString(100, 620, "Next Steps:")
        p.drawString(100, 600, summary.next_steps)
        
        p.showPage()
        p.save()
        return response
    except SessionSummary.DoesNotExist:
        messages.error(request, 'No summary available for this session')
        return redirect('telepsych_sessions:session_detail', session_id=session.id)

@login_required
@user_passes_test(lambda u: u.role == CustomUser.Roles.RESEARCHER)
def research_studies(request):
    researcher = get_object_or_404(Researcher, user=request.user)
    studies = researcher.studies.all()
    
    if request.method == 'POST':
        form = ResearchStudyForm(request.POST)
        if form.is_valid():
            study = form.save(commit=False)
            study.researcher = researcher
            study.save()
            messages.success(request, 'Research study created successfully')
            return redirect('telepsych_sessions:study_detail', study_id=study.id)
    else:
        form = ResearchStudyForm()
    
    return render(request, 'telepsych_sessions/research_studies.html', {
        'studies': studies,
        'form': form
    })

@login_required
@user_passes_test(lambda u: u.role == CustomUser.Roles.RESEARCHER)
def study_detail(request, study_id):
    study = get_object_or_404(ResearchStudy, id=study_id, researcher__user=request.user)
    participants = study.participants.all()
    surveys = study.surveys.all()
    
    if request.method == 'POST':
        form = ResearchSurveyForm(request.POST)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.study = study
            survey.save()
            messages.success(request, 'Survey created successfully')
            # Notify all study participants about the new survey
            for participant in study.participants.all():
                Notification.objects.create(
                    user=participant.patient.user,
                    message=f'New survey available for study "{study.title}": {survey.title}'
                )
            return redirect('telepsych_sessions:study_detail', study_id=study.id)
    else:
        form = ResearchSurveyForm()
    
    return render(request, 'telepsych_sessions/study_detail.html', {
        'study': study,
        'participants': participants,
        'surveys': surveys,
        'form': form
    })

@login_required
@user_passes_test(lambda u: u.role == CustomUser.Roles.RESEARCHER)
def manage_participants(request, study_id):
    study = get_object_or_404(ResearchStudy, id=study_id, researcher__user=request.user)
    participants = study.participants.all()

    if request.method == 'POST':
        participant_id = request.POST.get('participant_id')
        if participant_id:
            # Update existing participant
            participant = get_object_or_404(StudyParticipant, id=participant_id, study=study)
            form = StudyParticipantForm(request.POST, instance=participant, study=study)
            if form.is_valid():
                form.save()
                messages.success(request, 'Participant status updated')
                return redirect('telepsych_sessions:manage_participants', study_id=study.id)
        else:
            # Add new participant
            form = StudyParticipantForm(request.POST, study=study)
            if form.is_valid():
                new_participant = form.save(commit=False)
                new_participant.study = study
                new_participant.save()
                messages.success(request, 'Participant added successfully')
                return redirect('telepsych_sessions:manage_participants', study_id=study.id)
    else:
        form = StudyParticipantForm(study=study)

    return render(request, 'telepsych_sessions/manage_participants.html', {
        'study': study,
        'participants': participants,
        'form': form
    })

@login_required
@user_passes_test(lambda u: u.role == CustomUser.Roles.RESEARCHER)
def study_data(request, study_id):
    study = get_object_or_404(ResearchStudy, id=study_id, researcher__user=request.user)
    data = ResearchData.objects.filter(study=study).select_related('participant', 'session')
    
    # Group data by participant and data type
    data_by_participant = {}
    for item in data:
        if item.participant not in data_by_participant:
            data_by_participant[item.participant] = {}
        if item.data_type not in data_by_participant[item.participant]:
            data_by_participant[item.participant][item.data_type] = []
        data_by_participant[item.participant][item.data_type].append(item)
    
    return render(request, 'telepsych_sessions/study_data.html', {
        'study': study,
        'data_by_participant': data_by_participant
    })

@login_required
@user_passes_test(lambda u: u.role == CustomUser.Roles.RESEARCHER)
def survey_responses(request, study_id, survey_id):
    study = get_object_or_404(ResearchStudy, id=study_id, researcher__user=request.user)
    survey = get_object_or_404(ResearchSurvey, id=survey_id, study=study)
    responses = survey.responses.all().select_related('participant')
    
    return render(request, 'telepsych_sessions/survey_responses.html', {
        'study': study,
        'survey': survey,
        'responses': responses
    })

@login_required
def take_survey(request, study_id, survey_id):
    # Only allow patients
    if not hasattr(request.user, 'patient'):
        return redirect('telepsych_sessions:patient_dashboard')
    patient = request.user.patient
    study_participant = StudyParticipant.objects.filter(study_id=study_id, patient=patient, status='ACTIVE').first()
    if not study_participant:
        # Auto-enroll patient as a participant if not already
        from .models import ResearchStudy
        study = ResearchStudy.objects.get(id=study_id)
        study_participant = StudyParticipant.objects.create(study=study, patient=patient, status='ACTIVE')
    survey = ResearchSurvey.objects.get(id=survey_id, study_id=study_id, is_active=True)
    # Prevent retake
    if SurveyResponse.objects.filter(survey=survey, participant=study_participant).exists():
        messages.info(request, 'You have already completed this survey.')
        return redirect('telepsych_sessions:patient_dashboard')
    # Dynamically build form from survey.questions (assume list of dicts with 'question' key)
    import json
    questions = survey.questions if isinstance(survey.questions, list) else json.loads(survey.questions)
    class DynamicSurveyForm(Form):
        pass
    for idx, q in enumerate(questions):
        field_name = f'q_{idx}'
        DynamicSurveyForm.base_fields[field_name] = CharField(label=q['question'], required=True)
    if request.method == 'POST':
        form = DynamicSurveyForm(request.POST)
        if form.is_valid():
            answers = []
            for idx, q in enumerate(questions):
                answers.append({'question': q['question'], 'answer': form.cleaned_data[f'q_{idx}']})
            SurveyResponse.objects.create(survey=survey, participant=study_participant, answers=answers)
            messages.success(request, 'Survey submitted successfully!')
            return redirect('telepsych_sessions:patient_dashboard')
    else:
        form = DynamicSurveyForm()
    return render(request, 'telepsych_sessions/take_survey.html', {
        'survey': survey,
        'form': form,
        'study': study_participant.study,
    })

@login_required
@user_passes_test(lambda u: u.role == CustomUser.Roles.RESEARCHER)
def participant_detail(request, study_id, participant_id):
    study = get_object_or_404(ResearchStudy, id=study_id, researcher__user=request.user)
    participant = get_object_or_404(StudyParticipant, id=participant_id, study=study)
    return render(request, 'telepsych_sessions/participant_detail.html', {
        'study': study,
        'participant': participant,
    })

@login_required
@user_passes_test(lambda u: u.role == CustomUser.Roles.RESEARCHER)
def participant_surveys(request, study_id, participant_id):
    study = get_object_or_404(ResearchStudy, id=study_id, researcher__user=request.user)
    participant = get_object_or_404(StudyParticipant, id=participant_id, study=study)
    surveys = study.surveys.all()
    # Get responses for this participant
    responses = {resp.survey_id: resp for resp in participant.responses.all()}
    return render(request, 'telepsych_sessions/participant_surveys.html', {
        'study': study,
        'participant': participant,
        'surveys': surveys,
        'responses': responses,
    })

@login_required
@user_passes_test(lambda u: u.role == CustomUser.Roles.RESEARCHER)
@require_POST
def update_participant_status(request, study_id, participant_id):
    study = get_object_or_404(ResearchStudy, id=study_id, researcher__user=request.user)
    participant = get_object_or_404(StudyParticipant, id=participant_id, study=study)
    
    # Get the new status from the form
    new_status = request.POST.get('status')
    if new_status in dict(StudyParticipant._meta.get_field('status').choices):
        participant.status = new_status
        participant.save()
        messages.success(request, f'Participant status updated to {participant.get_status_display()}')
    else:
        messages.error(request, 'Invalid status value')
    
    return redirect('telepsych_sessions:manage_participants', study_id=study.id)

@login_required
@user_passes_test(lambda u: u.role == CustomUser.Roles.RESEARCHER)
@require_POST
def remove_participant(request, study_id, participant_id):
    study = get_object_or_404(ResearchStudy, id=study_id, researcher__user=request.user)
    participant = get_object_or_404(StudyParticipant, id=participant_id, study=study)
    
    # Delete the participant
    participant.delete()
    messages.success(request, 'Participant removed successfully')
    
    return redirect('telepsych_sessions:manage_participants', study_id=study.id)

def view_psychiatrist_profile(request, psychiatrist_id):
    psychiatrist = get_object_or_404(Psychiatrist, id=psychiatrist_id)
    return render(request, 'profile/psychiatrist_profile_public.html', {'psychiatrist': psychiatrist})

@require_GET
@login_required
def api_unread_chat_count(request):
    from .views import get_unread_chat_count
    count = get_unread_chat_count(request.user)
    return JsonResponse({'unread_chat_count': count})
