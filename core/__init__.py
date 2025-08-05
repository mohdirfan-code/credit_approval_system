# version: '3.9'

# services:
#   db:
#     image: postgres:15
#     environment:
#       POSTGRES_DB: credit_system
#       POSTGRES_USER: credituser
#       POSTGRES_PASSWORD: creditpass
#     ports:
#       - "5432:5432"
#     volumes:
#       - postgres_data:/var/lib/postgresql/data

#   redis:
#     image: redis:7
#     ports:
#       - "6379:6379"

#   web:
#     build: .
#     command: /app/entrypoint.sh
#     volumes:
#       - .:/app
#     ports:
#       - "8000:8000"
#     env_file:
#       - .env
#     depends_on:
#       - db
#       - redis

#   worker:
#     build: .
#     command: celery -A credit_system worker -l info
#     volumes:
#       - .:/app
#     env_file:
#       - .env
#     depends_on:
#       - db
#       - redis

# volumes:
#   postgres_data: