from celery import Celery
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def make_celery(app_name=__name__):
    broker_url = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    
    celery = Celery(
        app_name,
        broker=broker_url,
        backend=result_backend,
        include=['app.tasks.task_loader']
    )
    
    celery.conf.update(
        worker_max_tasks_per_child=1000,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        broker_connection_retry_on_startup=True,
        result_expires=3600,  # Results expire after 1 hour
    )
    
    return celery

# Create Celery app
celery_app = make_celery()

# Add periodic task for daily loader
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Run every day at midnight
    sender.add_periodic_task(
        crontab(hour=0, minute=0),
        task_loader.load_active_tasks.s(),
        name='Load active tasks daily'
    )