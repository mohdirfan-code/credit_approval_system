# core/tasks.py
import pandas as pd
from celery import shared_task
from django.db import transaction
from datetime import datetime
from .models import Customer, Loan

@shared_task
def ingest_customer_and_loan_data(customer_xlsx_path, loan_xlsx_path):
    """
    Ingests customer and loan data from Excel files into the database.
    """
    try:
        with transaction.atomic():
            # Ingest Customer Data
            customer_df = pd.read_excel(customer_xlsx_path)
            for _, row in customer_df.iterrows():
                customer_id = row.get("Customer ID") or row.get("id")
                Customer.objects.update_or_create(
                    customer_id=customer_id,
                    defaults={
                        "first_name": row["First Name"],
                        "last_name": row["Last Name"],
                        "age": row["Age"],
                        "phone_number": str(int(row["Phone Number"])),
                        "monthly_salary": row["Monthly Salary"],
                        "approved_limit": row["Approved Limit"],
                        "current_debt": 0  # Assuming initial debt is 0
                    }
                )
            
            # Ingest Loan Data
            loan_df = pd.read_excel(loan_xlsx_path)
            for _, row in loan_df.iterrows():
                try:
                    customer = Customer.objects.get(customer_id=row["Customer ID"])
                    
                    # Convert date columns to datetime objects, handling different formats
                    date_of_approval = row["Date of Approval"]
                    if isinstance(date_of_approval, datetime):
                        start_date = date_of_approval.date()
                    else:
                        start_date = datetime.strptime(str(date_of_approval), "%d-%m-%Y").date()

                    end_date_val = row["End Date"]
                    if isinstance(end_date_val, datetime):
                        end_date = end_date_val.date()
                    else:
                        end_date = datetime.strptime(str(end_date_val), "%d-%m-%Y").date()

                    loan_id = row.get("Loan ID")
                    Loan.objects.update_or_create(
                        loan_id=loan_id,
                        defaults={
                            "customer": customer,
                            "loan_amount": row["Loan Amount"],
                            "tenure": row["Tenure"],
                            "interest_rate": row["Interest Rate"],
                            "monthly_installment": row["Monthly payment"],
                            "emis_paid_on_time": row["EMIs paid on Time"],
                            "date_of_approval": start_date,
                            "end_date": end_date
                        }
                    )
                except Customer.DoesNotExist:
                    print(f"Customer with ID {row['Customer ID']} not found. Skipping loan ingestion for this record.")
                    continue
                except Exception as e:
                    print(f"Error processing row for Loan ID {row.get('Loan ID', 'Unknown')}: {e}")
                    continue

        return "Data ingestion completed successfully."

    except FileNotFoundError as e:
        return f"File not found: {e}"
    except Exception as e:
        return f"An error occurred: {e}"