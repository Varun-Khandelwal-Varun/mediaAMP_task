import io
import csv
import pandas as pd
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import BaseModel, validator, Field
from typing import Optional
import redis
import json
from app.models import db
from app.models.task_manager import TaskManager
from app.models.task_logger import TaskLogger
from app.models.user import User
from app.services.task_service import TaskService
from app import limiter

task_bp = Blueprint('task', __name__)
task_service = TaskService()

# Initialize Redis for caching
def get_redis_connection():
    return redis.Redis.from_url(current_app.config['REDIS_URL'])

# Input validation models
class TaskCreateModel(BaseModel):
    task_name: str
    description: Optional[str] = None
    status: bool = True
    priority: str
    assigned_user_id: Optional[int] = None
    
    @validator('priority')
    def validate_priority(cls, v):
        valid_priorities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        if v not in valid_priorities:
            raise ValueError(f"Priority must be one of {', '.join(valid_priorities)}")
        return v


class TaskUpdateModel(BaseModel):
    task_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[bool] = None
    priority: Optional[str] = None
    assigned_user_id: Optional[int] = None
    
    @validator('priority')
    def validate_priority(cls, v):
        if v is not None:
            valid_priorities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
            if v not in valid_priorities:
                raise ValueError(f"Priority must be one of {', '.join(valid_priorities)}")
        return v


@task_bp.route('/upload-csv', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def upload_csv():
    """
    Upload CSV file to load tasks into TaskManager
    ---
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: CSV file to upload
    responses:
      200:
        description: File uploaded successfully
      400:
        description: Invalid file or format
      401:
        description: Unauthorized
    """
    try:
        if 'file' not in request.files:
            return jsonify({"message": "No file part"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"message": "No selected file"}), 400
            
        if not file.filename.endswith('.csv'):
            return jsonify({"message": "Only CSV files are allowed"}), 400
        
        # Read CSV using pandas
        df = pd.read_csv(file.stream)
        
        # Validate required columns
        required_columns = ['task_name', 'description', 'status', 'priority', 'created_at', 'assigned_user']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({"message": f"Missing columns: {', '.join(missing_columns)}"}), 400
        
        # Process CSV data
        tasks_created = task_service.create_tasks_from_dataframe(df)
        
        return jsonify({
            "message": "CSV file processed successfully",
            "tasks_created": tasks_created
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Error processing file: {str(e)}"}), 400


@task_bp.route('/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    """
    Get paginated list of tasks from TaskLogger
    ---
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: Page number
      - name: per_page
        in: query
        type: integer
        default: 10
        description: Number of tasks per page
      - name: date
        in: query
        type: string
        format: date
        description: Filter tasks by specific date (YYYY-MM-DD)
    responses:
      200:
        description: List of tasks
      401:
        description: Unauthorized
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    date_str = request.args.get('date')
    
    # If date is provided, check Redis cache first
    if date_str:
        try:
            # Validate date format
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Check cache
            redis_conn = get_redis_connection()
            cache_key = f"tasks:date:{date_str}:page:{page}:per_page:{per_page}"
            cached_data = redis_conn.get(cache_key)
            
            if cached_data:
                return jsonify(json.loads(cached_data)), 200
                
            # Get data from database
            tasks, total, pages = task_service.get_tasks_by_date(
                filter_date, page, per_page
            )
            
            response = {
                "tasks": tasks,
                "total": total,
                "pages": pages,
                "current_page": page,
                "per_page": per_page
            }
            
            # Cache the result (expire after 1 hour)
            redis_conn.setex(
                cache_key,
                3600,  # 1 hour in seconds
                json.dumps(response)
            )
            
            return jsonify(response), 200
            
        except ValueError:
            return jsonify({"message": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    # If no date filter, get paginated tasks
    tasks, total, pages = task_service.get_paginated_tasks(page, per_page)
    
    return jsonify({
        "tasks": tasks,
        "total": total,
        "pages": pages,
        "current_page": page,
        "per_page": per_page
    }), 200


@task_bp.route('/task/<int:task_logger_id>', methods=['GET'])
@jwt_required()
def get_task(task_logger_id):
    """
    Get a specific task by ID
    ---
    parameters:
      - name: task_logger_id
        in: path
        type: integer
        required: true
        description: ID of the task to retrieve
    responses:
      200:
        description: Task details
      404:
        description: Task not found
      401:
        description: Unauthorized
    """
    task = task_service.get_task_by_id(task_logger_id)
    
    if not task:
        return jsonify({"message": "Task not found"}), 404
        
    return jsonify(task), 200


@task_bp.route('/task', methods=['POST'])
@jwt_required()
@limiter.limit("50 per hour")
def create_task():
    """
    Create a new task
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: Task
          properties:
            task_name:
              type: string
              description: Task name
            description:
              type: string
              description: Task description
            status:
              type: boolean
              description: Task status (active/inactive)
            priority:
              type: string
              description: Task priority (LOW, MEDIUM, HIGH, CRITICAL)
            assigned_user_id:
              type: integer
              description: ID of the user assigned to the task
    responses:
      201:
        description: Task created successfully
      400:
        description: Invalid input
      401:
        description: Unauthorized
    """
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        task_data = TaskCreateModel(**data)
        
        # Create task
        task = task_service.create_task(
            task_name=task_data.task_name,
            description=task_data.description,
            status=task_data.status,
            priority=task_data.priority,
            assigned_user_id=task_data.assigned_user_id or current_user_id,
            created_by_id=current_user_id
        )
        
        return jsonify({
            "message": "Task created successfully",
            "id": task.id,
            "task_name": task.task_name
        }), 201
        
    except ValueError as e:
        return jsonify({"message": str(e)}), 400


@task_bp.route('/task/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    """
    Update an existing task
    ---
    parameters:
      - name: task_id
        in: path
        type: integer
        required: true
        description: ID of the task to update
      - name: body
        in: body
        required: true
        schema:
          id: TaskUpdate
          properties:
            task_name:
              type: string
              description: Task name
            description:
              type: string
              description: Task description
            status:
              type: boolean
              description: Task status (active/inactive)
            priority:
              type: string
              description: Task priority (LOW, MEDIUM, HIGH, CRITICAL)
            assigned_user_id:
              type: integer
              description: ID of the user assigned to the task
    responses:
      200:
        description: Task updated successfully
      400:
        description: Invalid input
      403:
        description: Forbidden - Not authorized
      404:
        description: Task not found
      401:
        description: Unauthorized
    """
    @task_bp.route('/task/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    """
    Update an existing task
    ---
    parameters:
      - name: task_id
        in: path
        type: integer
        required: true
        description: ID of the task to update
      - name: body
        in: body
        required: true
        schema:
          id: TaskUpdate
          properties:
            task_name:
              type: string
              description: Task name
            description:
              type: string
              description: Task description
            status:
              type: boolean
              description: Task status (active/inactive)
            priority:
              type: string
              description: Task priority (LOW, MEDIUM, HIGH, CRITICAL)
            assigned_user_id:
              type: integer
              description: ID of the user assigned to the task
    responses:
      200:
        description: Task updated successfully
      400:
        description: Invalid input
      403:
        description: Forbidden - Not authorized
      404:
        description: Task not found
      401:
        description: Unauthorized
    """
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        task_update_data = TaskUpdateModel(**data)
        
        # Check if task exists
        task = task_service.get_task_manager_by_id(task_id)
        if not task:
            return jsonify({"message": "Task not found"}), 404
        
        # Check if user is authorized to update this task
        user = User.query.get(current_user_id)
        if not (task.assigned_user_id == current_user_id or 
                (user and user.has_role('admin'))):
            return jsonify({"message": "You are not authorized to update this task"}), 403
        
        # Update task
        updated_task = task_service.update_task(
            task_id=task_id,
            task_name=task_update_data.task_name,
            description=task_update_data.description,
            status=task_update_data.status,
            priority=task_update_data.priority,
            assigned_user_id=task_update_data.assigned_user_id,
            updated_by_id=current_user_id
        )
        
        # Clear cache for affected date
        if updated_task:
            redis_conn = get_redis_connection()
            # Clear all cached entries that might have this task
            for key in redis_conn.scan_iter("tasks:date:*"):
                redis_conn.delete(key)
        
        return jsonify({
            "message": "Task updated successfully",
            "id": updated_task.id,
            "task_name": updated_task.task_name
        }), 200
        
    except ValueError as e:
        return jsonify({"message": str(e)}), 400


@task_bp.route('/task/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    """
    Soft delete a task (mark as inactive)
    ---
    parameters:
      - name: task_id
        in: path
        type: integer
        required: true
        description: ID of the task to delete
    responses:
      200:
        description: Task deleted successfully
      403:
        description: Forbidden - Not authorized
      404:
        description: Task not found
      401:
        description: Unauthorized
    """
    current_user_id = get_jwt_identity()
    
    # Check if task exists
    task = task_service.get_task_manager_by_id(task_id)
    if not task:
        return jsonify({"message": "Task not found"}), 404
    
    # Check if user is authorized to delete this task
    user = User.query.get(current_user_id)
    if not (task.assigned_user_id == current_user_id or 
            (user and user.has_role('admin'))):
        return jsonify({"message": "You are not authorized to delete this task"}), 403
    
    # Soft delete task (mark as inactive)
    success = task_service.soft_delete_task(task_id, current_user_id)
    
    if success:
        # Clear cache for affected task
        redis_conn = get_redis_connection()
        for key in redis_conn.scan_iter("tasks:date:*"):
            redis_conn.delete(key)
            
        return jsonify({"message": "Task deleted successfully"}), 200
    else:
        return jsonify({"message": "Error deleting task"}), 500