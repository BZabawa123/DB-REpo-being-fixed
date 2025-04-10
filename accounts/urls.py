from django.urls import path
from .views import home
from .views import register, login_view
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', home, name='home'),  # Add this for the homepage
    path('login/', login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),  # Logout
    path('register/', views.register, name='register'),
    path('create_event/', views.create_event, name='create_event'),
    path('add_comment/<int:event_id>/', views.add_comment, name='add_comment'),
    path('edit_comment/<int:comment_id>/', views.edit_comment, name='edit_comment'),
    path('delete_comment/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    path('create-university/', views.create_university, name='create_university'),
    path('rso/create/', views.create_rso, name='create_rso'),
    path('rso/join/', views.join_rso, name='join_rso'),
    path('rso/my-rsos/', views.my_rsos, name='my_rsos'),
    path('rso/leave/<int:rso_id>/', views.leave_rso, name='leave_rso'),
]