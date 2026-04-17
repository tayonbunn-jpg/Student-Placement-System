from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.authentication.models import ActivityLog

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            ActivityLog.objects.create(
                user=user,
                action='user_register',
                description='New user registered.',
                metadata={'username': user.username}
            )
            messages.success(request, 'Account created successfully! You can now login.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'auth/register.html', {'form': form})

def dashboard_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')