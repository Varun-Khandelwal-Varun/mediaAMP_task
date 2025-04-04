from datetime import datetime, date
from sqlalchemy import func
from celery.utils.log import get_task_logger
from app.models import db
from app.models.task_manager import TaskManager
from app.models.task_logger import TaskLogger
from .celery_config import celery_app

logger = get_task_logger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def load_active_tasks(self):
    """
    Celery task to load active tasks from TaskManager to TaskLogger
    Runs daily and logs only active tasks
    """
    today = date.today()
    logger.info(f"Starting daily task loader for {today}")
    
    try:
        # Create Flask app context
        from app import create_app
        app = create_app()
        
        with app.app_context():
            # Check if tasks already loaded for today
            existing_count = TaskLogger.query.filter(
                TaskLogger.log_date == today
            ).count()
            
            if existing_count > 0:
                logger.info(f"Tasks already loaded for {today}. Skipping.")
                return f"Tasks already loaded for {today}. Found {existing_count} entries."
                
            # Get active tasks from TaskManager
            active_tasks = TaskManager.query.filter_by(status=True).all()
            logger.info(f"Found {len(active_tasks)} active tasks to load")
            
            # Create TaskLogger entries
            for task in active_tasks:
                log_entry = TaskLogger(
                    task_id=task.id,
                    log_date=today,
                    status=task.status,
                    priority=task.priority
                )
                db.session.add(log_entry)
                
            db.session.commit()
            logger.info(f"Successfully loaded {len(active_tasks)} tasks for {today}")
            
            return f"Successfully loaded {len(active_tasks)} tasks for {today}"
            
    except Exception as e:
        logger.error(f"Error loading tasks: {str(e)}")
        # Retry with exponential backoff
        self.retry(exc=e)
        
    return "Task completed with errors"


@celery_app.task
def manual_load_tasks():
    """
    Manually triggered task to load active tasks from TaskManager to TaskLogger
    """
    return load_active_tasks()