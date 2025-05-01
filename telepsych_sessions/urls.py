from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'telepsych_sessions'

urlpatterns = [
    # Public Pages
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    
    # Patient URLs
    path('patient/dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('patient/book-session/', views.book_session, name='book_session'),
    path('patient/health-records/', views.patient_health_records, name='patient_health_records'),
    path('patient/medications/', views.patient_medications, name='patient_medications'),
    path('patient/study/<int:study_id>/survey/<int:survey_id>/take/', views.take_survey, name='take_survey'),
    
    # Psychiatrist URLs
    path('psychiatrist/dashboard/', views.psychiatrist_dashboard, name='psychiatrist_dashboard'),
    path('psychiatrist/manage-sessions/', views.manage_sessions, name='manage_sessions'),
    path('session/<int:session_id>/accept/', views.accept_session, name='accept_session'),
    path('session/<int:session_id>/reject/', views.reject_session, name='reject_session'),
    
    # Common URLs
    path('session/<int:session_id>/cancel/', views.cancel_session, name='cancel_session'),
    path('session/<int:session_id>/review/', views.submit_review, name='submit_review'),
    path('session/<int:session_id>/chat/', views.session_chat, name='session_chat'),
    path('session/<int:session_id>/chat/ajax/', views.session_chat_ajax, name='session_chat_ajax'),
    path('session/<int:session_id>/typing/', views.set_typing_status, name='set_typing_status'),
    path('session/<int:session_id>/typing/status/', views.get_typing_status, name='get_typing_status'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    
    # Researcher URLs
    path('researcher/dashboard/', views.researcher_dashboard, name='researcher_dashboard'),
    path('researcher/studies/', views.research_studies, name='research_studies'),
    path('researcher/studies/<int:study_id>/', views.study_detail, name='study_detail'),
    path('researcher/studies/<int:study_id>/participants/', views.manage_participants, name='manage_participants'),
    path('researcher/studies/<int:study_id>/data/', views.study_data, name='study_data'),
    path('researcher/studies/<int:study_id>/surveys/<int:survey_id>/responses/', views.survey_responses, name='survey_responses'),
    path('chat/message/<int:message_id>/edit/', views.edit_message, name='edit_message'),
    path('chat/message/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('session/<int:session_id>/chat/search/', views.search_chat, name='search_chat'),
    path('chats/', views.chats_list, name='chats_list'),
    path('profile/', views.view_profile, name='view_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('notifications/history/', views.notifications_history, name='notifications_history'),
    path('chat_files/<path:filename>/', views.serve_chat_file, name='serve_chat_file'),
    path('sessions/<int:session_id>/reschedule/', views.reschedule_session, name='reschedule_session'),
    path('sessions/<int:session_id>/', views.session_detail, name='session_detail'),
    path('sessions/<int:session_id>/summary/create/', views.create_session_summary, name='create_session_summary'),
    path('sessions/<int:session_id>/summary/download/', views.download_session_summary, name='download_session_summary'),
    path('researcher/studies/<int:study_id>/participants/<int:participant_id>/', views.participant_detail, name='participant_detail'),
    path('researcher/studies/<int:study_id>/participants/<int:participant_id>/surveys/', views.participant_surveys, name='participant_surveys'),
    path('researcher/studies/<int:study_id>/participants/<int:participant_id>/update_status/', views.update_participant_status, name='update_participant_status'),
    path('researcher/studies/<int:study_id>/participants/<int:participant_id>/remove/', views.remove_participant, name='remove_participant'),
    path('psychiatrist/<int:psychiatrist_id>/profile/', views.view_psychiatrist_profile, name='view_psychiatrist_profile'),
    path('api/unread_chat_count/', views.api_unread_chat_count, name='api_unread_chat_count'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
