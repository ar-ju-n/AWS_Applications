from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views_researcher import researcher_dashboard, researcher_profile

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('password/change/', views.change_password, name='change_password'),
    path('password/reset/', views.reset_password, name='reset_password'),
    path('password/reset/done/', views.reset_password_done, name='reset_password_done'),
    path('password/reset/confirm/<uidb64>/<token>/', views.reset_password_confirm, name='reset_password_confirm'),
    path('password/reset/complete/', views.reset_password_complete, name='reset_password_complete'),
    path('researcher/dashboard/', researcher_dashboard, name='researcher_dashboard'),
    path('researcher/profile/', researcher_profile, name='researcher_profile'),
]
