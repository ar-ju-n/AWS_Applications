from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models_researcher import Researcher
from .forms_researcher import ResearcherProfileForm
from telepsych_sessions.models import Session

@login_required
def researcher_dashboard(request):
    if request.user.role != 'RESEARCHER':
        return redirect('home')
    
    researcher = get_object_or_404(Researcher, user=request.user)
    sessions = researcher.get_sessions_access()
    
    return render(request, 'accounts/researcher_dashboard.html', {
        'researcher': researcher,
        'sessions': sessions,
    })

@login_required
def researcher_profile(request):
    if request.user.role != 'RESEARCHER':
        return redirect('home')
    
    try:
        researcher = request.user.researcher_profile
    except Researcher.DoesNotExist:
        researcher = Researcher(user=request.user)
    
    if request.method == 'POST':
        form = ResearcherProfileForm(request.POST, instance=researcher)
        if form.is_valid():
            form.save()
            messages.success(request, 'Researcher profile updated successfully')
            return redirect('researcher_dashboard')
    else:
        form = ResearcherProfileForm(instance=researcher)
    
    return render(request, 'accounts/researcher_profile.html', {
        'form': form,
    })
