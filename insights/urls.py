from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),

    # Company filtering URLs
    path('filters/', views.company_filters, name='company_filters'),
    path('filters/create/', views.create_filter, name='create_filter'),
    path('filters/<int:filter_id>/edit/', views.edit_filter, name='edit_filter'),
    path('filters/<int:filter_id>/delete/', views.delete_filter, name='delete_filter'),
    path('filters/<int:filter_id>/apply/', views.apply_filter, name='apply_filter'),
    path('companies/save/<str:symbol>/', views.save_company, name='save_company'),
    path('companies/saved/', views.saved_companies, name='saved_companies'),
    path('companies/saved/<int:company_id>/remove/', views.remove_saved_company, name='remove_saved_company'),
]