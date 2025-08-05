# core/urls.py
from django.urls import path
from .views import (
    RegisterCustomerAPI,
    CheckEligibilityAPI,
    CreateLoanAPI,
    ViewLoanAPI,
    ViewCustomerLoansAPI
)

urlpatterns = [
    path('register/', RegisterCustomerAPI.as_view(), name='register-customer'),
    path('check-eligibility/', CheckEligibilityAPI.as_view(), name='check-eligibility'),
    path('create-loan/', CreateLoanAPI.as_view(), name='create-loan'),
    path('view-loan/<int:loan_id>/', ViewLoanAPI.as_view(), name='view-loan'),
    path('view-loans/<int:customer_id>/', ViewCustomerLoansAPI.as_view(), name='view-loans'),
]