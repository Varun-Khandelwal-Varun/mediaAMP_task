from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

# Import models to make them available for migrations
from .task_manager import TaskManager
from .task_logger import TaskLogger
from .user import User, Role, UserRole