from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from .models import CompanyFilter, SavedCompany
from .services import FinnhubService

class RegisterForm(forms.Form):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        email = cleaned_data.get('email')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords don't match")

        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists")

        return cleaned_data

class LoginForm(forms.Form):
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']

class CompanyFilterForm(forms.ModelForm):
    class Meta:
        model = CompanyFilter
        fields = ['name', 'exchange', 'sector', 'min_market_cap', 'max_market_cap',
                 'min_price', 'max_price', 'min_volume', 'min_pe_ratio', 'max_pe_ratio']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Tech Growth Stocks'}),
            'exchange': forms.Select(attrs={'class': 'form-select'}),
            'sector': forms.Select(attrs={'class': 'form-select'}),
            'min_market_cap': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1000'}),
            'max_market_cap': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '100000'}),
            'min_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '10.00'}),
            'max_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '500.00'}),
            'min_volume': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1000000'}),
            'min_pe_ratio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '5.00'}),
            'max_pe_ratio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '30.00'}),
        }

def home(request):
    return render(request, 'home.html')

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Create user with email as username
            user = User.objects.create_user(
                username=form.cleaned_data['email'],
                email=form.cleaned_data['email'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                password=form.cleaned_data['password']
            )
            messages.success(request, f'Account created for {user.first_name}!')
            login(request, user)
            return redirect('profile')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            # Authenticate using email (which is stored as username)
            try:
                user = User.objects.get(email=email)
                user = authenticate(request, username=user.username, password=password)
                if user:
                    login(request, user)
                    return redirect('profile')
                else:
                    messages.error(request, 'Invalid email or password')
            except User.DoesNotExist:
                messages.error(request, 'Invalid email or password')
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')

@login_required
def profile(request):
    return render(request, 'registration/profile.html')

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your name has been updated!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'registration/edit_profile.html', {'form': form})

@login_required
def company_filters(request):
    """List all user's company filters"""
    filters = CompanyFilter.objects.filter(user=request.user)
    return render(request, 'company/filters.html', {'filters': filters})

@login_required
def create_filter(request):
    """Create a new company filter"""
    if request.method == 'POST':
        form = CompanyFilterForm(request.POST)
        if form.is_valid():
            filter_obj = form.save(commit=False)
            filter_obj.user = request.user
            filter_obj.save()
            messages.success(request, f'Filter "{filter_obj.name}" created successfully!')
            return redirect('apply_filter', filter_id=filter_obj.id)
    else:
        form = CompanyFilterForm()
    return render(request, 'company/create_filter.html', {'form': form})

@login_required
def edit_filter(request, filter_id):
    """Edit an existing company filter"""
    filter_obj = get_object_or_404(CompanyFilter, id=filter_id, user=request.user)
    if request.method == 'POST':
        form = CompanyFilterForm(request.POST, instance=filter_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Filter "{filter_obj.name}" updated successfully!')
            return redirect('company_filters')
    else:
        form = CompanyFilterForm(instance=filter_obj)
    return render(request, 'company/edit_filter.html', {'form': form, 'filter': filter_obj})

@login_required
def delete_filter(request, filter_id):
    """Delete a company filter"""
    filter_obj = get_object_or_404(CompanyFilter, id=filter_id, user=request.user)
    if request.method == 'POST':
        filter_name = filter_obj.name
        filter_obj.delete()
        messages.success(request, f'Filter "{filter_name}" deleted successfully!')
        return redirect('company_filters')
    return render(request, 'company/delete_filter.html', {'filter': filter_obj})

@login_required
def apply_filter(request, filter_id):
    """Apply a filter and show matching companies"""
    filter_obj = get_object_or_404(CompanyFilter, id=filter_id, user=request.user)

    companies = []
    error_message = None

    try:
        finnhub_service = FinnhubService()
        companies = finnhub_service.filter_companies(filter_obj, limit=25)

        if not companies:
            messages.info(request, 'No companies found matching your criteria. Try adjusting your filters.')

    except Exception as e:
        error_message = f"Error fetching companies: {str(e)}"
        messages.error(request, error_message)

    context = {
        'filter': filter_obj,
        'companies': companies,
        'error_message': error_message
    }
    return render(request, 'company/results.html', context)

@login_required
def save_company(request, symbol):
    """Save a company to user's saved list"""
    try:
        finnhub_service = FinnhubService()
        profile = finnhub_service.get_company_profile(symbol)
        quote = finnhub_service.get_quote(symbol)

        if profile and quote:
            saved_company, created = SavedCompany.objects.get_or_create(
                user=request.user,
                symbol=symbol,
                defaults={
                    'name': profile.get('name', ''),
                    'exchange': profile.get('exchange', ''),
                    'sector': profile.get('finnhubIndustry', ''),
                    'market_cap': profile.get('marketCapitalization', 0),
                    'price': quote.get('c', 0),
                }
            )

            if created:
                messages.success(request, f'{symbol} saved to your watchlist!')
            else:
                messages.info(request, f'{symbol} is already in your watchlist.')
        else:
            messages.error(request, f'Could not fetch data for {symbol}')

    except Exception as e:
        messages.error(request, f'Error saving company: {str(e)}')

    return redirect(request.META.get('HTTP_REFERER', 'company_filters'))

@login_required
def saved_companies(request):
    """Show user's saved companies"""
    companies = SavedCompany.objects.filter(user=request.user)
    return render(request, 'company/saved.html', {'companies': companies})

@login_required
def remove_saved_company(request, company_id):
    """Remove a company from saved list"""
    company = get_object_or_404(SavedCompany, id=company_id, user=request.user)
    company_name = company.symbol
    company.delete()
    messages.success(request, f'{company_name} removed from your watchlist.')
    return redirect('saved_companies')
