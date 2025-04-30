from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import PermissionDenied
import os
import logging
from django.conf import settings
from .models import Session, Patient, Psychiatrist, SessionMessage, SessionTypingStatus
from accounts.models import CustomUser
from .forms import SessionBookingForm, SessionReviewForm, SessionMessageForm
from .forms_profile import PatientProfileForm, PsychiatristProfileForm, UserProfileForm
from .models_notification import Notification
import uuid
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt

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
    
    return render(request, 'patient_dashboard.html', {
        'sessions': sessions.order_by('-scheduled_time'),
        'status_filter': status_filter,
        'psychiatrist_filter': psychiatrist_filter,
        'available_psychiatrists': available_psychiatrists,
        'unread_count': unread_count,
        'unread_chat_count': unread_chat_count,
        'notifications': notifications,
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
    if hasattr(user, 'patient'):
        profile = user.patient
        form_class = PatientProfileForm
        success_url = 'telepsych_sessions:patient_dashboard'
    elif hasattr(user, 'psychiatrist'):
        profile = user.psychiatrist
        form_class = PsychiatristProfileForm
        success_url = 'telepsych_sessions:psychiatrist_dashboard'
    elif user.role == CustomUser.Roles.PSYCHIATRIST:
        # If psychiatrist profile does not exist, create it
        from .models import Psychiatrist
        from django.utils import timezone
        unique_license = f"TEMP-{user.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        profile = Psychiatrist.objects.create(user=user, specialization='', license_number=unique_license, availability=[], bio='')
        form_class = PsychiatristProfileForm
        success_url = 'telepsych_sessions:psychiatrist_dashboard'
    else:
        messages.error(request, 'Profile not found.')
        return redirect('telepsych_sessions:index')

    if request.method == 'POST':
        form = form_class(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect(success_url)
    else:
        form = form_class(instance=profile)
    return render(request, 'complete_profile.html', {'form': form})

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
def edit_profile(request):
    user = request.user
    user_form = UserProfileForm(instance=user)
    profile_form = None
    
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=user)
        if user.role == 'PSYCHIATRIST':
            profile_form = PsychiatristProfileForm(request.POST, instance=user.psychiatrist)
        elif user.role == 'PATIENT':
            profile_form = PatientProfileForm(request.POST, instance=user.patient)
            
        if user_form.is_valid() and (profile_form is None or profile_form.is_valid()):
            user_form.save()
            if profile_form:
                profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('telepsych_sessions:view_profile')
    else:
        if user.role == 'PSYCHIATRIST':
            profile_form = PsychiatristProfileForm(instance=user.psychiatrist)
        elif user.role == 'PATIENT':
            profile_form = PatientProfileForm(instance=user.patient)
    
    return render(request, 'edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'user': user
    })

@login_required
def notifications_history(request):
    notifications = request.user.notifications.order_by('-created_at')
    return render(request, 'notifications_history.html', {'notifications': notifications})
