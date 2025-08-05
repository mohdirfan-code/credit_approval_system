# This file marks this directory as a Python package.
from .celery import app as celery_app

__all__ = ("celery_app",)