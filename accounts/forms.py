from django import forms
from .models import Users, Events, EventCreation, RSOs
from django.contrib.auth.forms import AuthenticationForm
from django.core.validators import EmailValidator

class UserRegistrationForm(forms.ModelForm):
    role = forms.ChoiceField(choices=Users.USER_ROLES)

    class Meta:
        model = Users
        fields = ['username', 'email', 'password', 'role']
        widgets = {
            'password': forms.PasswordInput(),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])  # Hash the password
        if commit:
            user.save()
        return user

class UserLoginForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)


class EventCreationForm(forms.ModelForm):
    class Meta:
        model = Events
        fields = ['event_name', 'category', 'description', 'event_date', 'start_time', 'end_time', 'lname']

class EventPrivacyForm(forms.Form):
    privacy_choices = [
        ('Public', 'Public'),
        ('Private', 'Private'),
    ]
    privacy = forms.ChoiceField(choices=privacy_choices)
    rso = forms.ModelChoiceField(queryset=RSOs.objects.all(), required=False)  # Only for RSO even

class EventForm(forms.ModelForm):
    class Meta:
        model = Events
        fields = ['event_name', 'category', 'description', 'event_date', 'start_time', 'end_time', 'lname']


class CreateRSOForm(forms.ModelForm):
    name = forms.CharField(max_length=80, required=True, 
                          widget=forms.TextInput(attrs={'class': 'form-control'}))
    description = forms.CharField(required=True, 
                                widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    
    # Fields for additional members
    member1_email = forms.EmailField(required=True, 
                                   widget=forms.EmailInput(attrs={'class': 'form-control'}))
    member2_email = forms.EmailField(required=True, 
                                   widget=forms.EmailInput(attrs={'class': 'form-control'}))
    member3_email = forms.EmailField(required=True, 
                                   widget=forms.EmailInput(attrs={'class': 'form-control'}))
    member4_email = forms.EmailField(required=True, 
                                   widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = RSOs
        fields = ['name', 'description']
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Get the emails for validation
        creator_email = self.creator.email
        member_emails = [
            cleaned_data.get('member1_email'),
            cleaned_data.get('member2_email'),
            cleaned_data.get('member3_email'),
            cleaned_data.get('member4_email')
        ]
        
        # Check if all emails have the same domain
        creator_domain = get_university_domain(creator_email)
        
        for email in member_emails:
            if email:
                member_domain = get_university_domain(email)
                if member_domain != creator_domain:
                    raise forms.ValidationError(
                        f"All members must have the same email domain as you ({creator_domain}.edu)"
                    )
        
        # Check if all members exist in the system
        for email in member_emails:
            if email:
                try:
                    Users.objects.get(email=email)
                except Users.DoesNotExist:
                    raise forms.ValidationError(
                        f"User with email {email} is not registered in the system"
                    )
        
        # Check for duplicate emails
        unique_emails = set(member_emails)
        if len(unique_emails) != 4:
            raise forms.ValidationError("All member emails must be unique")
        
        # Ensure creator's email is not in the member list
        if creator_email in member_emails:
            raise forms.ValidationError("You cannot include your own email in the member list")
        
        return cleaned_data
    
    def __init__(self, *args, **kwargs):
        self.creator = kwargs.pop('user', None)
        super(CreateRSOForm, self).__init__(*args, **kwargs)


class JoinRSOForm(forms.Form):
    rso = forms.ModelChoiceField(
        queryset=RSOs.objects.filter(status='active'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select an RSO to join"
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        university_id = kwargs.pop('university_id', None)
        super(JoinRSOForm, self).__init__(*args, **kwargs)
        
        if university_id:
            # Only show RSOs from the user's university
            self.fields['rso'].queryset = RSOs.objects.filter(
                university_id=university_id,
                status='active'
            )


# utils.py
def get_university_domain(email):
    """Extract the university domain from an email address."""
    if '@' in email and '.edu' in email:
        domain = email.split('@')[1]
        return domain.split('.edu')[0]  # 'knights' from abc@knights.ucf.edu
    return None

def get_university_from_email(email):
    """Get the university object based on the email domain."""
    from .models import Universities
    
    domain = get_university_domain(email)
    if domain:
        # Try to find university with matching domain in name
        try:
            # This assumes the university name contains the domain somewhere
            # You might need to adjust this logic based on your data
            university = Universities.objects.filter(name__icontains=domain).first()
            return university
        except Universities.DoesNotExist:
            return None
    return None