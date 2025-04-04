from datetime import datetime
from sqlalchemy import event
from . import db

class TaskManager(db.Model):
    """TaskManager model for storing task information"""
    __tablename__ = 'task_manager'
    
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.Boolean, default=True, index=True)  # True for active, False for inactive
    priority = db.Column(db.String(20), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign key relationship
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # One-to-many relationship with TaskLogger
    logs = db.relationship('TaskLogger', backref='task', lazy='dynamic',
                           cascade='all, delete-orphan')
    
    # Add audit log entries
    audit_logs = db.relationship('TaskAuditLog', backref='task', lazy='dynamic',
                                cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Task {self.task_name}>"


class TaskAuditLog(db.Model):
    """Model for tracking changes to task statuses"""
    __tablename__ = 'task_audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task_manager.id'), nullable=False)
    previous_status = db.Column(db.Boolean)
    new_status = db.Column(db.Boolean)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    changed_by = db.relationship('User')


# SQLAlchemy event listener to track status changes
@event.listens_for(TaskManager.status, 'set')
def task_status_change_handler(target, value, oldvalue, initiator):
    if oldvalue is not None and oldvalue != value:
        audit_log = TaskAuditLog(
            task_id=target.id,
            previous_status=oldvalue,
            new_status=value
        )
        db.session.add(audit_log)