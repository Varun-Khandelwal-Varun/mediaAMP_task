from datetime import datetime
from sqlalchemy import func
from app.models import db
from app.models.task_manager import TaskManager, TaskAuditLog
from app.models.task_logger import TaskLogger
from app.models.user import User


class TaskService:
    def create_tasks_from_dataframe(self, df):
        """
        Create tasks from pandas DataFrame
        
        Args:
            df (pandas.DataFrame): DataFrame with task data
            
        Returns:
            int: Number of tasks created
        """
        tasks_created = 0
        
        for _, row in df.iterrows():
            # Convert status to boolean
            status = True
            if isinstance(row['status'], str):
                status = row['status'].lower() in ['true', 'yes', 'y', '1']
            elif isinstance(row['status'], (int, bool)):
                status = bool(row['status'])
            
            # Get or create user
            user = User.query.filter_by(username=row['assigned_user']).first()
            if not user:
                user = User(
                    username=row['assigned_user'],
                    email=f"{row['assigned_user']}@example.com"  # Placeholder email
                )
                user.password = "DefaultPassword123"  # Default password
                db.session.add(user)
                db.session.flush()  # Get the ID without committing
            
            # Create task
            task = TaskManager(
                task_name=row['task_name'],
                description=row['description'],
                status=status,
                priority=row['priority'],
                assigned_user_id=user.id
            )
            
            # Handle created_at if provided
            if 'created_at' in row and row['created_at']:
                try:
                    if isinstance(row['created_at'], str):
                        task.created_at = datetime.strptime(row['created_at'], '%m/%d/%Y')
                except ValueError:
                    # If date parsing fails, use current date
                    pass
            
            db.session.add(task)
            tasks_created += 1
        
        db.session.commit()
        return tasks_created
    
    def get_paginated_tasks(self, page=1, per_page=10):
        """
        Get paginated tasks from TaskLogger
        
        Args:
            page (int): Page number
            per_page (int): Number of items per page
            
        Returns:
            tuple: (tasks list, total count, total pages)
        """
        pagination = TaskLogger.query.order_by(
            TaskLogger.log_date.desc(), 
            TaskLogger.id.desc()
        ).paginate(page=page, per_page=per_page)
        
        tasks = []
        for log in pagination.items:
            task = {
                'id': log.id,
                'task_id': log.task_id,
                'log_date': log.log_date.strftime('%Y-%m-%d'),
                'status': log.status,
                'priority': log.priority,
                'task_name': log.task.task_name if log.task else None,
                'description': log.task.description if log.task else None,
                'assigned_user': log.task.assigned_user.username if log.task and log.task.assigned_user else None
            }
            tasks.append(task)
        
        return tasks, pagination.total, pagination.pages
    
    def get_tasks_by_date(self, date, page=1, per_page=10):
        """
        Get tasks filtered by date
        
        Args:
            date (datetime.date): Date to filter by
            page (int): Page number
            per_page (int): Number of items per page
            
        Returns:
            tuple: (tasks list, total count, total pages)
        """
        pagination = TaskLogger.query.filter(
            TaskLogger.log_date == date
        ).order_by(
            TaskLogger.id.desc()
        ).paginate(page=page, per_page=per_page)
        
        tasks = []
        for log in pagination.items:
            task = {
                'id': log.id,
                'task_id': log.task_id,
                'log_date': log.log_date.strftime('%Y-%m-%d'),
                'status': log.status,
                'priority': log.priority,
                'task_name': log.task.task_name if log.task else None,
                'description': log.task.description if log.task else None,
                'assigned_user': log.task.assigned_user.username if log.task and log.task.assigned_user else None
            }
            tasks.append(task)
        
        return tasks, pagination.total, pagination.pages
    
    def get_task_by_id(self, task_logger_id):
        """
        Get a specific task by TaskLogger ID
        
        Args:
            task_logger_id (int): TaskLogger ID
            
        Returns:
            dict: Task details or None if not found
        """
        log = TaskLogger.query.get(task_logger_id)
        
        if not log:
            return None
            
        task = {
            'id': log.id,
            'task_id': log.task_id,
            'log_date': log.log_date.strftime('%Y-%m-%d'),
            'status': log.status,
            'priority': log.priority,
            'task_name': log.task.task_name if log.task else None,
            'description': log.task.description if log.task else None,
            'assigned_user': log.task.assigned_user.username if log.task and log.task.assigned_user else None,
            'created_at': log.task.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.task else None,
            'updated_at': log.task.updated_at.strftime('%Y-%m-%d %H:%M:%S') if log.task else None
        }
        
        return task
    
    def get_task_manager_by_id(self, task_id):
        """
        Get a TaskManager by ID
        
        Args:
            task_id (int): TaskManager ID
            
        Returns:
            TaskManager: TaskManager object or None if not found
        """
        return TaskManager.query.get(task_id)
    
    def create_task(self, task_name, description, status, priority, assigned_user_id, created_by_id):
        """
        Create a new task
        
        Args:
            task_name (str): Task name
            description (str): Task description
            status (bool): Task status (active/inactive)
            priority (str): Task priority
            assigned_user_id (int): ID of the assigned user
            created_by_id (int): ID of the user creating the task
            
        Returns:
            TaskManager: Created task
        """
        task = TaskManager(
            task_name=task_name,
            description=description,
            status=status,
            priority=priority,
            assigned_user_id=assigned_user_id
        )
        
        db.session.add(task)
        db.session.commit()
        
        # Create audit log
        audit_log = TaskAuditLog(
            task_id=task.id,
            new_status=status,
            changed_by_id=created_by_id
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return task
    
    def update_task(self, task_id, updated_by_id, **kwargs):
        """
        Update an existing task
        
        Args:
            task_id (int): TaskManager ID
            updated_by_id (int): ID of the user updating the task
            **kwargs: Fields to update
            
        Returns:
            TaskManager: Updated task or None if not found
        """
        task = self.get_task_manager_by_id(task_id)
        
        if not task:
            return None
            
        # Track old status for audit log
        old_status = task.status
        
        # Update fields if provided
        for field, value in kwargs.items():
            if value is not None and hasattr(task, field):
                setattr(task, field, value)
                
        task.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Create audit log if status changed
        if 'status' in kwargs and kwargs['status'] is not None and old_status != kwargs['status']:
            audit_log = TaskAuditLog(
                task_id=task.id,
                previous_status=old_status,
                new_status=kwargs['status'],
                changed_by_id=updated_by_id
            )
            db.session.add(audit_log)
            db.session.commit()
        
        return task
    
    def soft_delete_task(self, task_id, deleted_by_id):
        """
        Soft delete a task (mark as inactive)
        
        Args:
            task_id (int): TaskManager ID
            deleted_by_id (int): ID of the user deleting the task
            
        Returns:
            bool: True if successful, False otherwise
        """
        task = self.get_task_manager_by_id(task_id)
        
        if not task:
            return False
            
        old_status = task.status
        task.status = False
        task.updated_at = datetime.utcnow()
        
        # Create audit log
        audit_log = TaskAuditLog(
            task_id=task.id,
            previous_status=old_status,
            new_status=False,
            changed_by_id=deleted_by_id
        )
        
        db.session.add(audit_log)
        db.session.commit()
        
        return True