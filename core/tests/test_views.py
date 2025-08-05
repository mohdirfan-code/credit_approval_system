# core/tests/test_views.py
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from core.models import Customer, Loan
from datetime import date
from django.utils import timezone
import datetime

class CreditSystemAPITest(APITestCase):

    def setUp(self):
        self.customer_data_high_income = {
            "first_name": "Test",
            "last_name": "User",
            "age": 35,
            "monthly_income": Decimal('100000'),
            "phone_number": "1234567890"
        }
        self.customer_data_low_income = {
            "first_name": "Poor",
            "last_name": "User",
            "age": 45,
            "monthly_income": Decimal('10000'),
            "phone_number": "0987654321"
        }
        # Register a customer to be used in other tests
        response = self.client.post('/api/register/', self.customer_data_high_income, format='json')
        self.high_income_customer_id = response.data['customer_id']

        # Create a loan in setUp to make sure view_customer_loans test passes
        self.test_loan = Loan.objects.create(
            customer_id=self.high_income_customer_id,
            loan_amount=Decimal('500000'),
            tenure=24,
            interest_rate=Decimal('10.50'),
            monthly_installment=Decimal('23000'),
            emis_paid_on_time=0,
            date_of_approval=timezone.now().date(),
            end_date=timezone.now().date() + datetime.timedelta(days=30 * 24)
        )

    def test_register_customer_success(self):
        """
        Test that a new customer can be registered successfully.
        """
        response = self.client.post('/api/register/', self.customer_data_low_income, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('customer_id', response.data)
        self.assertEqual(response.data['name'], "Poor User")
        self.assertEqual(response.data['approved_limit'], Decimal('400000'))

    def test_check_eligibility_approved(self):
        """
        Test that a loan is approved for a high credit score customer.
        """
        loan_request = {
            "customer_id": self.high_income_customer_id,
            "loan_amount": Decimal('500000'),
            "interest_rate": Decimal('8.0'),
            "tenure": 12
        }
        response = self.client.post('/api/check-eligibility/', loan_request, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['approval'])
        self.assertEqual(response.data['corrected_interest_rate'], 8.0)
        self.assertGreater(response.data['monthly_installment'], 0)

    def test_check_eligibility_interest_rate_correction(self):
        """
        Test that a loan's interest rate is corrected based on credit score rules.
        """
        # Create enough loans to bring the credit score into the correction range (30-50)
        for i in range(11):
            Loan.objects.create(
                customer_id=self.high_income_customer_id,
                loan_amount=Decimal('10000'),
                tenure=12,
                interest_rate=Decimal('10.00'),
                monthly_installment=Decimal('1000'),
                emis_paid_on_time=5,
                date_of_approval=date(2023, 1, 1),
                end_date=timezone.now().date() + datetime.timedelta(days=30 * 12)
            )
        loan_request = {
            "customer_id": self.high_income_customer_id,
            "loan_amount": Decimal('100000'),
            "interest_rate": Decimal('8.0'),
            "tenure": 12
        }
        response = self.client.post('/api/check-eligibility/', loan_request, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['approval'])
        self.assertEqual(response.data['corrected_interest_rate'], 12.0)
        self.assertGreater(response.data['monthly_installment'], 0)

    def test_check_eligibility_rejected_low_credit(self):
        """
        Test that a loan is rejected for a very low credit score.
        """
        # Create enough loans to bring the credit score below the rejection threshold (<=10)
        for i in range(20):
            Loan.objects.create(
                customer_id=self.high_income_customer_id,
                loan_amount=Decimal('10000'),
                tenure=10,
                interest_rate=Decimal('10.00'),
                monthly_installment=Decimal('1000'),
                emis_paid_on_time=5,
                date_of_approval=date(2023, 1, 1),
                end_date=date(2023, 11, 1)
            )

        loan_request = {
            "customer_id": self.high_income_customer_id,
            "loan_amount": Decimal('100000'),
            "interest_rate": Decimal('8.0'),
            "tenure": 12
        }
        response = self.client.post('/api/check-eligibility/', loan_request, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['approval'])
        self.assertIn("low credit score", response.data['message'])

    def test_create_loan_success(self):
        """
        Test that a loan is successfully created for an eligible customer.
        """
        loan_request = {
            "customer_id": self.high_income_customer_id,
            "loan_amount": Decimal('500000'),
            "interest_rate": Decimal('8.0'),
            "tenure": 12
        }
        response = self.client.post('/api/create-loan/', loan_request, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('loan_id', response.data)
        self.assertTrue(response.data['loan_approved'])

    def test_view_loan_details(self):
        """
        Test that the view-loan endpoint returns correct details.
        """
        response = self.client.get(f'/api/view-loan/{self.test_loan.loan_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['loan_id'], self.test_loan.loan_id)
        self.assertEqual(response.data['customer']['customer_id'], self.high_income_customer_id)

    def test_view_customer_loans(self):
        """
        Test that the view-loans endpoint returns a list of all loans for a customer.
        """
        response = self.client.get(f'/api/view-loans/{self.high_income_customer_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 1)