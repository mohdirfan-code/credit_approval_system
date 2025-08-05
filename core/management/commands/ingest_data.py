# core/management/commands/ingest_data.py
from django.core.management.base import BaseCommand
from core.tasks import ingest_customer_and_loan_data
import os

class Command(BaseCommand):
    help = 'Ingest customer and loan data from Excel files using a Celery background task.'

    def add_arguments(self, parser):
        parser.add_argument('--customer_xlsx', type=str, help='Path to the customer Excel file.')
        parser.add_argument('--loan_xlsx', type=str, help='Path to the loan Excel file.')

    def handle(self, *args, **options):
        customer_xlsx_path = options['customer_xlsx']
        loan_xlsx_path = options['loan_xlsx']

        if not customer_xlsx_path or not loan_xlsx_path:
            self.stdout.write(self.style.ERROR('Both --customer_xlsx and --loan_xlsx arguments are required.'))
            return

        self.stdout.write(self.style.NOTICE("Starting data ingestion task..."))
        
        # Trigger the Celery task and get the task ID
        task_result = ingest_customer_and_loan_data.delay(customer_xlsx_path, loan_xlsx_path)

        self.stdout.write(self.style.SUCCESS(f"Ingestion task triggered with ID: {task_result.id}"))
        self.stdout.write(self.style.NOTICE("Check worker logs for progress. Data will be available in the admin panel upon completion."))