# accounts/utils.py
from .models import Universities  # Assuming a Universities model exists

def get_university_from_email(email):
    university_name = get_university_name_from_email(email)
    if not university_name:
        return None
    try:
        return Universities.objects.get(name__icontains=university_name)
    except Universities.DoesNotExist:
        return None

def get_university_name_from_email(email):
    if '@' in email and '.edu' in email:
        domain = email.split('@')[1]
        return domain.split('.edu')[0]
    return None