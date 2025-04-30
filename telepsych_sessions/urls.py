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
    path('chat/message/<int:message_id>/edit/', views.edit_message, name='edit_message'),
    path('chat/message/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('session/<int:session_id>/chat/search/', views.search_chat, name='search_chat'),
    path('chats/', views.chats_list, name='chats_list'),
    path('profile/', views.view_profile, name='view_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('notifications/history/', views.notifications_history, name='notifications_history'),
    path('chat_files/<path:filename>/', views.serve_chat_file, name='serve_chat_file'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
