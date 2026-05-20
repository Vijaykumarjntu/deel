# from django.shortcuts import render

# Create your views here.
# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CompanySignupForm, ContractorForm
from .models import Company, Contractor
from django.views.decorators.csrf import csrf_exempt

def home(request):
    return render(request, 'core/home.html')


def signup(request):
    if request.method == 'POST':
        form = CompanySignupForm(request.POST)
        if form.is_valid():
            # Get data
            email = form.cleaned_data['email']
            password = form.cleaned_data['password1']
            company_name = form.cleaned_data['company_name']
            website = form.cleaned_data.get('website', '')
            
            # Create user manually (MORE RELIABLE)
            from .models import User
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                role='company'
            )
            
            # Create company
            Company.objects.create(
                user=user,
                name=company_name,
                website=website
            )
            
            # Log them in
            login(request, user)
            messages.success(request, f'Welcome {company_name}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please fix the errors below')
    else:
        form = CompanySignupForm()
    
    return render(request, 'core/signup.html', {'form': form})


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        print("passwored is ")
        print(password)
        print("email is ")
        print(email)
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials')
    return render(request, 'core/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')


# core/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# @login_required
# def dashboard(request):
#     # Hardcoded data for now
#     company = {
#         'name': request.user.email,  # Use email as company name
#         'stripe_verified': False,
#     }
    
#     contractors = [
#         {'full_name': 'John Contractor', 'country': 'India', 'is_active': True},
#         {'full_name': 'Jane Worker', 'country': 'Brazil', 'is_active': True},
#     ]
    
#     return render(request, 'core/company_dashboard.html', {
#         'company': company,
#         'contractors': contractors,
#     })


@login_required
def dashboard(request):
    
    if  request.user.role:
        company = request.user.company
        contractors = company.contractors.all()
        return render(request, 'core/company_dashboard.html', {
            'company': company,
            'contractors': contractors,
        })
    elif request.user.role == 'contractor':
        contractor = request.user.contractor
        contracts = contractor.contracts.all()
        return render(request, 'core/contractor_dashboard.html', {
            'contractor': contractor,
            'contracts': contracts,
        })
    return redirect('home')

@login_required
def add_contractor(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ContractorForm(request.POST, company=request.user.company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contractor added successfully!')
            return redirect('contractor_list')
    else:
        form = ContractorForm()
    
    return render(request, 'core/add_contractor.html', {'form': form})

@login_required
def contractor_list(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    contractors = request.user.company.contractors.all()
    return render(request, 'core/contractor_list.html', {'contractors': contractors})