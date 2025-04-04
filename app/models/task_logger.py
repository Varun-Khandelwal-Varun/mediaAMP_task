from datetime import datetime
from . import db

class TaskLogger(db.Model):
    """TaskLogger model for logging daily task status"""
    __tablename__ = 'task_logger'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task_manager.id'), nullable=False)
    log_date = db.Column(db.Date, default=datetime.utcnow().date, index=True)
    status = db.Column(db.Boolean)
    priority = db.Column(db.String(20))
    
    # Composite index for task_id and log_date to ensure uniqueness
    __table_args__ = (
        db.UniqueConstraint('task_id', 'log_date', name='unique_task_date'),
        db.Index('idx_task_logger_date', 'log_date'),
    )
    
    def __repr__(self):
        return f"<TaskLog {self.task_id} on {self.log_date}>"