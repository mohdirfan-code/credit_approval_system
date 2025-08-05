````markdown
# Credit Approval System

A production-grade backend service for a credit approval system built with Django REST Framework, using background workers for data ingestion and a Dockerized environment.

## Key Features

- **Customer Registration**: A public API endpoint to register new customers and automatically set a credit limit.
- **Loan Eligibility Check**: An API to evaluate a customer's credit score based on historical data and determine their eligibility for a new loan.
- **Loan Creation**: An API to process and create a new loan if the customer meets all eligibility criteria.
- **Data Ingestion**: An asynchronous Celery task to ingest initial customer and loan data from Excel files into the database.
- **Comprehensive API**: Endpoints for viewing single loan details and a list of all loans for a specific customer.
- **Dockerized Environment**: The entire application stack (Django, PostgreSQL, Redis, Celery) runs in isolated Docker containers.

---

## Prerequisites

To run this project, you need to have the following installed:

- **Docker**: [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose**: [Install Docker Compose](https://docs.docker.com/compose/install/)

---

## Getting Started

Follow these steps to set up and run the project locally.

### 1. Clone the Repository

```sh
git clone <YOUR_GITHUB_REPO_URL>
cd credit_approval_system
````

### 2\. Configure Environment Variables

Create a **`.env`** file in the project's root directory and populate it with your environment variables.

```env
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=*
POSTGRES_DB=credit_system
POSTGRES_USER=credituser
POSTGRES_PASSWORD=creditpass
POSTGRES_HOST=db
POSTGRES_PORT=5432
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### 3\. Run the Application

Build and start all the services using Docker Compose.

```sh
docker-compose up --build
```

This command will bring up the **`web`**, **`db`**, **`redis`**, and **`worker`** services. The Django migrations will run automatically on startup.

### 4\. Data Ingestion

The provided `customer_data.xlsx` and `loan_data.xlsx` files can be ingested into the database using a background worker.

1.  Place the `customer_data.xlsx` and `loan_data.xlsx` files in the **`data/`** directory at the project root.
2.  Run the management command from the `web` container:
    ```sh
    docker-compose exec web python manage.py ingest_data --customer_xlsx /app/data/customer_data.xlsx --loan_xlsx /app/data/loan_data.xlsx
    ```
3.  You can view the ingestion process by checking the logs of the `worker` container:
    ```sh
    docker-compose logs -f worker
    ```

-----

## API Documentation

The API is fully documented and interactive using Swagger UI.

  - **Swagger UI**: [http://localhost:8000/swagger/](https://www.google.com/search?q=http://localhost:8000/swagger/)
  - **ReDoc**: [http://localhost:8000/redoc/](https://www.google.com/search?q=http://localhost:8000/redoc/)

Here is a summary of the available endpoints:

**`POST /api/register/`**

  - **Description**: Registers a new customer.
  - **Request Body**:
    ```json
    {
      "first_name": "John",
      "last_name": "Doe",
      "age": 30,
      "monthly_income": 50000,
      "phone_number": "9876543210"
    }
    ```
  - **Response**: `201 Created` with new `customer_id` and `approved_limit`.

**`POST /api/check-eligibility/`**

  - **Description**: Checks a customer's loan eligibility and calculates a potential EMI.
  - **Request Body**:
    ```json
    {
      "customer_id": 1,
      "loan_amount": 500000,
      "interest_rate": 10.5,
      "tenure": 12
    }
    ```
  - **Response**: `200 OK` with `approval` status, `monthly_installment`, and a message.

**`POST /api/create-loan/`**

  - **Description**: Creates a new loan for an eligible customer.
  - **Request Body**: (Same as `check-eligibility`).
  - **Response**: `201 Created` with new `loan_id` if approved, or `200 OK` with `loan_id: null` if rejected.

**`GET /api/view-loan/{loan_id}/`**

  - **Description**: Retrieves details for a specific loan.
  - **Response**: `200 OK` with detailed loan and customer information.

**`GET /api/view-loans/{customer_id}/`**

  - **Description**: Retrieves all loans for a customer.
  - **Response**: `200 OK` with an array of loan objects, including `repayments_left`.

-----

## Unit Tests

This project includes a suite of unit tests for the core API endpoints and business logic. To run the tests:

```sh
docker-compose exec web python manage.py test core
```

-----

## Technology Stack

  - **Backend**: Python, Django 4+, Django Rest Framework
  - **Database**: PostgreSQL
  - **Caching/Broker**: Redis
  - **Asynchronous Tasks**: Celery
  - **Deployment**: Docker, Docker Compose

<!-- end list -->

```
```