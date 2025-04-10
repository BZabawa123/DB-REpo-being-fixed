from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from django.http import HttpResponseForbidden
from .forms import UserRegistrationForm, EventCreationForm, EventPrivacyForm, EventForm, CreateRSOForm, JoinRSOForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.urls import reverse
from django.db import transaction
from .models import Users, Events, Universities, RSOs, StudentsRSOs, RSOEvents, EventCreation, Comments
from .utils import get_university_from_email  # Add this import


def home(request):
    # Check if the user is authenticated
    if request.user.is_authenticated:
        user = request.user

        # SuperAdmin sees everything
        if user.role == 'SuperAdmin':
            events = Events.objects.all()
        else:
            email_university = get_university_name_from_email(user.email)

            # Public events
            public_events = Events.objects.filter(
                event_id__in=EventCreation.objects.filter(privacy='Public').values_list('event_id', flat=True)
            )

            # Private events for same university
            private_event_ids = EventCreation.objects.filter(
                privacy='Private',
                admin__email__icontains=f'@{email_university}.edu'
            ).values_list('event_id', flat=True)
            private_events = Events.objects.filter(event_id__in=private_event_ids)

            # RSO events for RSOs the user is in
            user_rso_ids = StudentsRSOs.objects.filter(uid=user).values_list('rso_id', flat=True)
            rso_event_ids = RSOEvents.objects.filter(rso_id__in=user_rso_ids).values_list('event_id', flat=True)
            rso_events = Events.objects.filter(event_id__in=rso_event_ids)

            # Combine all events
            events = public_events | private_events | rso_events

        events = events.distinct()  # avoid duplicates
    else:
        # If the user is not authenticated, return an empty events list
        events = []

    return render(request, 'accounts/home.html', {'events': events})

def get_university_name_from_email(email):
    if '@' in email and '.edu' in email:
        domain = email.split('@')[1]
        return domain.split('.edu')[0]  # 'name' from abc@name.edu
    return None



def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()  # Saves the user and hashes the password
            role = form.cleaned_data['role']
            if role == 'admin':
                user.is_staff = True
            elif role == 'superadmin':
                user.is_superuser = True
            user.save()  # Save changes to user
            login(request, user)  # Log the user in
            return redirect('home')  # Redirect to home page
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # Get the cleaned data
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            # Authenticate the user
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # Log the user in
                login(request, user)
                return redirect('home')  # Redirect to home or another page after login
            else:
                # Invalid credentials
                form.add_error(None, 'Invalid login credentials')
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def create_event(request):
    if request.method == 'POST':
        event_form = EventForm(request.POST)
        privacy_form = EventPrivacyForm(request.POST)
        
        if event_form.is_valid() and privacy_form.is_valid():
            event = event_form.save(commit=False)
            privacy = privacy_form.cleaned_data['privacy']
            
            # For non-public events (Private or RSO), assign university
            if privacy != 'Public':
                uni_name = get_university_name_from_email(request.user.email)
                university = Universities.objects.filter(name__icontains=uni_name).first()
                if not university:
                    event_form.add_error(None, "Could not find matching university for your email.")
                    return render(request, 'accounts/event_creation.html', {
                        'event_form': event_form,
                        'privacy_form': privacy_form
                    })
                event.university = university
            else:
                # Handle public events' university assignment
                # You might need to assign a default university for public events
                event.university = Universities.objects.first()  # or some default
                
            event.save()
            
            # Create EventCreation record
            creation = EventCreation.objects.create(
                event=event,
                admin=request.user,
                superadmin=Users.objects.filter(role='SuperAdmin').first(),
                privacy=privacy
            )
            
            # If it's a Private event with an RSO selected
            if privacy == 'Private' and privacy_form.cleaned_data.get('rso'):
                RSOEvents.objects.create(
                    event=event,
                    rso=privacy_form.cleaned_data['rso']
                )
                
            return redirect('home')
    else:
        event_form = EventForm()
        privacy_form = EventPrivacyForm()
        
    return render(request, 'accounts/event_creation.html', {
        'event_form': event_form,
        'privacy_form': privacy_form
    })


def add_comment(request, event_id):
    if not request.user.is_authenticated:
        return HttpResponse('')  # Blank response

    event = get_object_or_404(Events, event_id=event_id)

    if request.method == 'POST':
        content = request.POST.get('content')
        rating = request.POST.get('rating')

        if content and rating:
            Comments.objects.create(
                uid=request.user,
                event=event,
                content=content,
                rating=rating
            )
            messages.success(request, 'Your comment was added successfully!')
        else:
            messages.error(request, 'There was an error with your comment.')

    return redirect('home')


def edit_comment(request, comment_id):
    if not request.user.is_authenticated:
        return HttpResponse('')  # Blank response

    comment = get_object_or_404(Comments, comment_id=comment_id, uid=request.user)

    if request.method == 'POST':
        content = request.POST.get('content')
        rating = request.POST.get('rating')

        if content and rating:
            comment.content = content
            comment.rating = rating
            comment.save()
            messages.success(request, 'Your comment was updated successfully!')
            return redirect('home')
        else:
            messages.error(request, 'There was an error updating your comment.')

    # Simple form data for editing (you can customize this HTML or template later)
    return render(request, 'accounts/edit_comment.html', {
        'comment': comment
    })


def delete_comment(request, comment_id):
    if not request.user.is_authenticated:
        return HttpResponse('')  # Blank response

    comment = get_object_or_404(Comments, comment_id=comment_id, uid=request.user)

    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Your comment was deleted successfully!')

    return redirect('home')

def create_university(request):
    if request.method == 'POST':
        if request.user.is_authenticated and request.user.role == 'SuperAdmin':
            # Get form data
            name = request.POST.get('name')
            location = request.POST.get('location')
            description = request.POST.get('description')
            number_of_students = request.POST.get('number_of_students')
            
            # Validate data
            if not all([name, location, description, number_of_students]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'accounts/create_university.html')
            
            try:
                # Create university
                university = Universities(
                    name=name,
                    location=location,
                    description=description,
                    number_of_students=int(number_of_students)
                )
                university.save()
                
                messages.success(request, f'University "{name}" has been successfully created!')
                return redirect('home')  # Redirect to homepage after success
                
            except Exception as e:
                messages.error(request, f'Error creating university: {str(e)}')
                return render(request, 'create_university.html')
        else:
            messages.error(request, 'You do not have permission to create universities.')
            return redirect('home')
    else:
        # GET request - just render the form
        return render(request, 'accounts/create_university.html')

def create_rso(request):
    """View for creating a new RSO."""
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to create an RSO.")
        return redirect('login')
    
    # Only students can create RSOs
    if request.user.role != 'Student':
        messages.error(request, "Only students can create RSOs.")
        return redirect('home')
    
    # Get the user's university from their email
    university = get_university_from_email(request.user.email)
    if not university:
        messages.error(request, "Your email domain is not associated with any university in our system.")
        return redirect('home')
    
    if request.method == 'POST':
        form = CreateRSOForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create the RSO
                    rso = form.save(commit=False)
                    rso.university = university
                    rso.admin = request.user
                    rso.status = 'inactive'  # Start as inactive until approved
                    rso.save()
                    
                    # Add the creator as a member
                    StudentsRSOs.objects.create(uid=request.user, rso=rso)
                    
                    # Add the other members with error handling
                    for i in range(1, 5):
                        member_email = form.cleaned_data[f'member{i}_email']
                        try:
                            member = Users.objects.get(email=member_email)
                            StudentsRSOs.objects.create(uid=member, rso=rso)
                        except Users.DoesNotExist:
                            messages.error(request, f"Member with email {member_email} not found.")
                            raise  # Rollback transaction
                    
                    # If we have 5 members (creator + 4), set the RSO to active
                    if StudentsRSOs.objects.filter(rso=rso).count() >= 5:
                        rso.status = 'active'
                        rso.save()
                    
                    messages.success(request, f"RSO '{rso.name}' has been created successfully.")
                    return redirect('home')
            
            except Exception as e:
                messages.error(request, f"Error creating RSO: {str(e)}")
    else:
        form = CreateRSOForm(user=request.user)
    
    return render(request, 'accounts/create_rso.html', {
        'form': form,
        'university': university
    })


def join_rso(request):
    """View for joining an existing RSO."""
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to join an RSO.")
        return redirect('login')
    
    # Get the user's university from their email
    university = get_university_from_email(request.user.email)
    if not university:
        messages.error(request, "Your email domain is not associated with any university in our system.")
        return redirect('home')
    
    # Check if the user already has RSO memberships
    user_rsos = StudentsRSOs.objects.filter(uid=request.user).select_related('rso')
    
    if request.method == 'POST':
        form = JoinRSOForm(request.POST, user=request.user, university_id=university.university_id)
        if form.is_valid():
            rso = form.cleaned_data['rso']
            
            # Check if user is already a member
            if StudentsRSOs.objects.filter(uid=request.user, rso=rso).exists():
                messages.info(request, f"You are already a member of '{rso.name}'.")
                return redirect('home')
            
            # Join the RSO
            StudentsRSOs.objects.create(uid=request.user, rso=rso)
            messages.success(request, f"You have successfully joined '{rso.name}'.")
            return redirect('home')
    else:
        form = JoinRSOForm(user=request.user, university_id=university.university_id)
    
    return render(request, 'accounts/join_rso.html', {
        'form': form,
        'university': university,
        'user_rsos': user_rsos
    })


def my_rsos(request):
    """View to display the user's RSO memberships."""
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to view your RSOs.")
        return redirect('login')
    
    # Get RSOs where the user is a member
    memberships = StudentsRSOs.objects.filter(uid=request.user).select_related('rso')
    
    # Get RSOs where the user is an admin
    admin_rsos = RSOs.objects.filter(admin=request.user)
    
    return render(request, 'accounts/my_rsos.html', {
        'memberships': memberships,
        'admin_rsos': admin_rsos
    })


def leave_rso(request, rso_id):
    """View for leaving an RSO."""
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to leave an RSO.")
        return redirect('login')
    
    rso = get_object_or_404(RSOs, rso_id=rso_id)
    
    # Check if user is a member
    membership = StudentsRSOs.objects.filter(uid=request.user, rso=rso).first()
    if not membership:
        messages.error(request, f"You are not a member of '{rso.name}'.")
        return redirect('my_rsos')
    
    # Check if user is the admin of the RSO
    if rso.admin == request.user:
        messages.error(request, f"As the admin of '{rso.name}', you cannot leave the RSO. You must transfer administration first.")
        return redirect('my_rsos')
    
    # Leave the RSO
    membership.delete()
    
    # Check if RSO still has enough members
    member_count = StudentsRSOs.objects.filter(rso=rso).count()
    if member_count < 5 and rso.status == 'active':
        rso.status = 'inactive'
        rso.save()
        messages.warning(request, f"'{rso.name}' now has fewer than 5 members and has been set to inactive.")
    
    messages.success(request, f"You have successfully left '{rso.name}'.")
    return redirect('my_rsos')