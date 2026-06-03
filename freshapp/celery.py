import os
from celery import Celery

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "freshapp.settings",
)

app = Celery("freshapp")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
