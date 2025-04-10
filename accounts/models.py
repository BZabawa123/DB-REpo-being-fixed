from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class UsersManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)  # Ensure password is hashed
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        return self.create_user(username, email, password, **extra_fields)


class Users(AbstractBaseUser, PermissionsMixin):
    uid = models.AutoField(primary_key=True)
    username = models.CharField(max_length=80, unique=True)
    email = models.EmailField(max_length=80, unique=True)
    password = models.CharField(max_length=100)
    USER_ROLES = (
        ('SuperAdmin', 'SuperAdmin'),
        ('Admin', 'Admin'),
        ('Student', 'Student')
    )

    role = models.CharField(
        max_length=10,
        choices=USER_ROLES,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    REQUIRED_FIELDS = ['email']
    USERNAME_FIELD = 'username'

    objects = UsersManager()

    class Meta:
        db_table = 'Users'


class Universities(models.Model):
    university_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=80)
    location = models.CharField(max_length=80)
    description = models.TextField()
    number_of_students = models.IntegerField()

    class Meta:
        db_table = 'Universities'


class RSOs(models.Model):
    rso_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=80)
    university = models.ForeignKey(Universities, on_delete=models.DO_NOTHING, db_column='university_id')
    admin = models.ForeignKey(Users, on_delete=models.DO_NOTHING, db_column='admin_id')
    status = models.CharField(max_length=10, choices=[
        ('active', 'active'),
        ('inactive', 'inactive')
    ], default='inactive')

    class Meta:
        db_table = 'RSOs'


class Locations(models.Model):
    # Primary key needs to be shorter to avoid index length issues
    lname = models.CharField(primary_key=True, max_length=80)
    address = models.CharField(max_length=80)
    longitude = models.FloatField()
    latitude = models.FloatField()

    class Meta:
        db_table = 'Locations'
        managed = True


class Events(models.Model):
    event_id = models.AutoField(primary_key=True)
    # Reduced from 191 to be safer with the composite index
    event_name = models.CharField(max_length=80)
    category = models.CharField(max_length=20, choices=[
        ('Social', 'Social'),
        ('Fundraising', 'Fundraising'),
        ('Tech Talk', 'Tech Talk')
    ])
    description = models.TextField()
    event_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    lname = models.ForeignKey(Locations, on_delete=models.DO_NOTHING, db_column='lname')
    university = models.ForeignKey(Universities, on_delete=models.DO_NOTHING, db_column='university_id')

    class Meta:
        db_table = 'Events'
        managed = True
        unique_together = (('lname', 'event_date', 'start_time'),)


class EventCreation(models.Model):
    event = models.OneToOneField(Events, on_delete=models.DO_NOTHING, primary_key=True, db_column='event_id')
    admin = models.ForeignKey(Users, on_delete=models.DO_NOTHING, related_name='admin_events', db_column='admin_id')
    superadmin = models.ForeignKey(Users, on_delete=models.DO_NOTHING, related_name='superadmin_events', db_column='superadmin_id')
    privacy = models.CharField(max_length=10, choices=[
        ('Public', 'Public'),
        ('Private', 'Private')
    ])

    class Meta:
        db_table = 'Event_Creation'


class RSOEvents(models.Model):
    event = models.OneToOneField(Events, on_delete=models.DO_NOTHING, primary_key=True, db_column='event_id')
    rso = models.ForeignKey(RSOs, on_delete=models.DO_NOTHING, db_column='rso_id')

    class Meta:
        db_table = 'RSO_Events'


class Comments(models.Model):
    comment_id = models.AutoField(primary_key=True)
    uid = models.ForeignKey(Users, on_delete=models.DO_NOTHING, db_column='uid')
    event = models.ForeignKey(Events, on_delete=models.DO_NOTHING, db_column='event_id')
    rating = models.IntegerField()
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Comments'


class StudentsRSOs(models.Model):
    uid = models.ForeignKey(Users, on_delete=models.DO_NOTHING, db_column='uid')
    rso = models.ForeignKey(RSOs, on_delete=models.DO_NOTHING, db_column='rso_id')

    class Meta:
        db_table = 'Students_RSOs'
        unique_together = (('uid', 'rso'),)