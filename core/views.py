# core/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Q, F
from django.utils import timezone
from .models import Customer, Loan
from .serializers import (
    RegisterCustomerSerializer,
    CheckEligibilitySerializer,
    CreateLoanSerializer,
    LoanDetailSerializer,
    CustomerLoansSerializer
)
import math
from decimal import Decimal
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from collections import OrderedDict

# Define schemas for Swagger manually to avoid inference issues with APIView
register_customer_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties=OrderedDict([
        ('first_name', openapi.Schema(type=openapi.TYPE_STRING)),
        ('last_name', openapi.Schema(type=openapi.TYPE_STRING)),
        ('age', openapi.Schema(type=openapi.TYPE_INTEGER)),
        ('monthly_income', openapi.Schema(type=openapi.TYPE_NUMBER)),
        ('phone_number', openapi.Schema(type=openapi.TYPE_STRING)),
    ]),
)

check_eligibility_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties=OrderedDict([
        ('customer_id', openapi.Schema(type=openapi.TYPE_INTEGER)),
        ('loan_amount', openapi.Schema(type=openapi.TYPE_NUMBER)),
        ('interest_rate', openapi.Schema(type=openapi.TYPE_NUMBER)),
        ('tenure', openapi.Schema(type=openapi.TYPE_INTEGER)),
    ]),
)

create_loan_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties=OrderedDict([
        ('customer_id', openapi.Schema(type=openapi.TYPE_INTEGER)),
        ('loan_amount', openapi.Schema(type=openapi.TYPE_NUMBER)),
        ('interest_rate', openapi.Schema(type=openapi.TYPE_NUMBER)),
        ('tenure', openapi.Schema(type=openapi.TYPE_INTEGER)),
    ]),
)

def calculate_eligibility(customer, loan_amount, interest_rate, tenure):
    """
    Helper function to calculate eligibility and credit score.
    Returns a dictionary of eligibility data.
    """
    # Check sum of all current EMIs > 50% of monthly salary
    active_loans = Loan.objects.filter(
        customer=customer,
        emis_paid_on_time__lt=F('tenure'),
        end_date__gte=timezone.now().date()
    )
    total_current_emi = active_loans.aggregate(Sum('monthly_installment'))['monthly_installment__sum'] or Decimal('0.00')
    
    if total_current_emi > (customer.monthly_salary / Decimal(2)):
        return {
            "approval": False,
            "message": "Loan not approved. Sum of current EMIs exceeds 50% of monthly salary.",
            "corrected_interest_rate": float(interest_rate),
            "monthly_installment": 0
        }

    # Credit Score Calculation
    credit_score = Decimal('100.00')
    
    # Past Loans paid on time (consider only closed loans for this metric)
    past_loans_paid_on_time = Loan.objects.filter(
        customer=customer,
        emis_paid_on_time__gte=F('tenure'),
        end_date__lt=timezone.now().date()
    ).count()
    credit_score += Decimal(str(past_loans_paid_on_time * 5))
    
    # No of loans taken in past (total loans, active or closed)
    total_loans_taken = Loan.objects.filter(customer=customer).count()
    if total_loans_taken > 0:
        credit_score -= Decimal(str(total_loans_taken * 5))
    
    # Loan activity in current year (number of loans approved in current year)
    current_year = timezone.now().year
    loans_this_year = Loan.objects.filter(customer=customer, date_of_approval__year=current_year).count()
    credit_score += Decimal(str(loans_this_year * 3))
    
    # Loan approved volume (sum of all current active loans)
    total_active_loan_amount = active_loans.aggregate(Sum('loan_amount'))['loan_amount__sum'] or Decimal('0.00')
    
    if total_active_loan_amount > customer.approved_limit:
        credit_score = Decimal('0.00')
    else:
        if customer.approved_limit > 0:
            volume_ratio = total_active_loan_amount / customer.approved_limit
            credit_score += Decimal(str(int(volume_ratio * 10)))
            
    credit_score = max(Decimal('0.00'), min(Decimal('100.00'), credit_score))
    
    # Eligibility based on credit score and interest rate rules
    approval = False
    corrected_interest_rate = Decimal(str(interest_rate))
    message = ""
    
    if credit_score > Decimal('50.00'):
        approval = True
    elif Decimal('50.00') >= credit_score > Decimal('30.00'):
        approval = True
        if corrected_interest_rate < Decimal('12.00'):
            corrected_interest_rate = Decimal('12.00')
            message = f"Interest rate corrected to {corrected_interest_rate}% (minimum for this credit score slab)."
    elif Decimal('30.00') >= credit_score > Decimal('10.00'):
        approval = True
        if corrected_interest_rate < Decimal('16.00'):
            corrected_interest_rate = Decimal('16.00')
            message = f"Interest rate corrected to {corrected_interest_rate}% (minimum for this credit score slab)."
    else:
        approval = False
        message = "Loan not approved due to low credit score (below 10)."
        
    if loan_amount > customer.approved_limit:
        approval = False
        message = "Loan not approved. Requested loan amount exceeds customer's approved limit."
        
    monthly_installment = Decimal('0.00')
    if approval:
        monthly_rate = (corrected_interest_rate / Decimal('12.00')) / Decimal('100.00')
        if monthly_rate > 0:
            monthly_installment = (loan_amount * monthly_rate) / (Decimal('1') - (Decimal('1') + monthly_rate)**(-tenure))
        else:
            monthly_installment = loan_amount / Decimal(tenure)
            
    return {
        "approval": approval,
        "message": message,
        "corrected_interest_rate": float(corrected_interest_rate),
        "monthly_installment": round(monthly_installment, 2)
    }

class RegisterCustomerAPI(APIView):
    @swagger_auto_schema(request_body=register_customer_schema)
    def post(self, request, *args, **kwargs):
        serializer = RegisterCustomerSerializer(data=request.data)
        if serializer.is_valid():
            monthly_income = serializer.validated_data['monthly_income']
            approved_limit = math.ceil((36 * monthly_income) / 100000) * 100000
            
            customer = Customer.objects.create(
                first_name=serializer.validated_data['first_name'],
                last_name=serializer.validated_data['last_name'],
                age=serializer.validated_data['age'],
                phone_number=serializer.validated_data['phone_number'],
                monthly_salary=monthly_income,
                approved_limit=approved_limit,
                current_debt=0
            )
            response_data = {
                "customer_id": customer.customer_id,
                "name": f"{customer.first_name} {customer.last_name}",
                "age": customer.age,
                "monthly_income": customer.monthly_salary,
                "approved_limit": customer.approved_limit,
                "phone_number": customer.phone_number
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CheckEligibilityAPI(APIView):
    @swagger_auto_schema(request_body=check_eligibility_schema)
    def post(self, request, *args, **kwargs):
        serializer = CheckEligibilitySerializer(data=request.data)
        if serializer.is_valid():
            customer_id = serializer.validated_data['customer_id']
            loan_amount = serializer.validated_data['loan_amount']
            interest_rate = serializer.validated_data['interest_rate']
            tenure = serializer.validated_data['tenure']
            
            try:
                customer = Customer.objects.get(customer_id=customer_id)
            except Customer.DoesNotExist:
                return Response({"error": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

            eligibility_data = calculate_eligibility(
                customer, 
                loan_amount, 
                interest_rate, 
                tenure
            )
            
            response_data = {
                "customer_id": customer.customer_id,
                "approval": eligibility_data['approval'],
                "interest_rate": float(interest_rate),
                "corrected_interest_rate": eligibility_data['corrected_interest_rate'],
                "tenure": tenure,
                "monthly_installment": eligibility_data['monthly_installment'],
                "message": eligibility_data['message']
            }
            return Response(response_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CreateLoanAPI(APIView):
    @swagger_auto_schema(request_body=create_loan_schema)
    def post(self, request, *args, **kwargs):
        serializer = CreateLoanSerializer(data=request.data)
        if serializer.is_valid():
            customer_id = serializer.validated_data['customer_id']
            loan_amount = serializer.validated_data['loan_amount']
            interest_rate = serializer.validated_data['interest_rate']
            tenure = serializer.validated_data['tenure']

            try:
                customer = Customer.objects.get(customer_id=customer_id)
            except Customer.DoesNotExist:
                return Response({"error": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

            eligibility_data = calculate_eligibility(
                customer, 
                loan_amount, 
                interest_rate, 
                tenure
            )
            
            if not eligibility_data['approval']:
                return Response({
                    "loan_id": None,
                    "customer_id": customer.customer_id,
                    "loan_approved": False,
                    "message": eligibility_data["message"],
                    "monthly_installment": None
                }, status=status.HTTP_200_OK)
            
            corrected_interest_rate = Decimal(str(eligibility_data.get('corrected_interest_rate', interest_rate)))
            monthly_installment = Decimal(str(eligibility_data.get('monthly_installment', Decimal('0.00'))))

            loan = Loan.objects.create(
                customer=customer,
                loan_amount=loan_amount,
                tenure=tenure,
                interest_rate=corrected_interest_rate,
                monthly_installment=monthly_installment,
                date_of_approval=timezone.now().date(),
                end_date=timezone.now().date() + timezone.timedelta(days=30 * tenure),
                emis_paid_on_time=0
            )
            
            customer.current_debt += loan_amount
            customer.save()

            return Response({
                "loan_id": loan.loan_id,
                "customer_id": customer.customer_id,
                "loan_approved": True,
                "message": "Loan approved successfully.",
                "monthly_installment": round(monthly_installment, 2)
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ViewLoanAPI(APIView):
    def get(self, request, loan_id, *args, **kwargs):
        try:
            loan = Loan.objects.select_related('customer').get(loan_id=loan_id)
            serializer = LoanDetailSerializer(loan)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Loan.DoesNotExist:
            return Response({"error": "Loan not found."}, status=status.HTTP_404_NOT_FOUND)

class ViewCustomerLoansAPI(APIView):
    def get(self, request, customer_id, *args, **kwargs):
        try:
            customer = Customer.objects.get(customer_id=customer_id)
            loans = Loan.objects.filter(customer=customer)
            serializer = CustomerLoansSerializer(loans, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)