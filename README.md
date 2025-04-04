# Task Manager API

A high-performance Flask backend for task management that ensures data integrity, performance, security, and scalability.

## Tech Stack

* **Python Flask** - Web framework
* **SQLAlchemy** - ORM for database operations
* **Celery** - Distributed task queue
* **PostgreSQL** - Primary database
* **Redis** - Caching and message broker
* **Docker** - Containerization

## Features

* Well-structured modular architecture with Blueprints, Services, and Repositories
* Secure database connection with connection pooling and retry mechanism
* Role-based access control (RBAC)
* Audit logging for task changes
* Distributed task processing with Celery
* API security with JWT authentication, rate limiting, and input validation
* Optimized database queries with lazy loading and indexing
* Redis caching for improved performance

## Project Structure

```
task_manager/
├── docker/               # Docker configuration
├── app/                  # Application code
│   ├── __init__.py       # App initialization
│   ├── config.py         # Configuration
│   ├── models/           # Database models
│   ├── api/              # API endpoints
│   ├── services/         # Business logic
│   ├── repositories/     # Data access
│   ├── utils/            # Utility functions
│   ├── tasks/            # Celery tasks
├── migrations/           # Database migrations
├── tests/                # Test suite
├── .env.example          # Environment variables template
├── requirements.txt      # Python dependencies
├── run.py                # Application entry point
```

## Setup Instructions

### Prerequisites

* Docker and Docker Compose
* Git

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/task-manager-api.git
   cd task-manager-api
   ```

2. Create environment file from template:
   ```bash
   cp .env.example .env
   ```

3. Modify the `.env` file with your settings (generate strong secret keys).

4. Build and start the containers:
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

5. Initialize the database:
   ```bash
   docker-compose -f docker/docker-compose.yml exec app flask db init
   docker-compose -f docker/docker-compose.yml exec app flask db migrate -m "Initial migration"
   docker-compose -f docker/docker-compose.yml exec app flask db upgrade
   ```

6. Create an admin user:
   ```bash
   docker-compose -f docker/docker-compose.yml exec app python -c "from app import create_app; from app.services.auth_service import AuthService; app = create_app(); with app.app_context(): AuthService().create_user('admin', 'admin@example.com', 'SecurePassword123', roles=['admin', 'user'])"
   ```

### Running Tests

```bash
docker-compose -f docker/docker-compose.yml exec app pytest
```

## API Reference

### Authentication Endpoints

#### Register a new user
```
POST /api/register
```
Request body:
```json
{
  "username": "user123",
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

#### Login
```
POST /api/login
```
Request body:
```json
{
  "username": "user123",
  "password": "SecurePassword123"
}
```
Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "Login successful",
  "username": "user123"
}
```

### Task Endpoints

#### Upload CSV
```
POST /api/upload-csv
```
Form data:
- `file`: CSV file with task data

#### Get all tasks (paginated)
```
GET /api/tasks?page=1&per_page=10
```

#### Get tasks by date
```
GET /api/tasks?date=2025-04-01
```

#### Get task details
```
GET /api/task/{task_logger_id}
```

#### Create a task
```
POST /api/task
```
Request body:
```json
{
  "task_name": "New Task",
  "description": "Task description",
  "status": true,
  "priority": "HIGH",
  "assigned_user_id": 1
}
```

#### Update a task
```
PUT /api/task/{task_id}
```
Request body:
```json
{
  "task_name": "Updated Task",
  "priority": "MEDIUM"
}
```

#### Delete a task
```
DELETE /api/task/{task_id}
```

## Security Features

* Environment variables for storing credentials
* JWT-based authentication
* Role-based access control
* Input validation with Pydantic
* Rate limiting and throttling
* Secure password storage with hashing

## Performance Optimizations

* Connection pooling for database
* Redis caching for frequently accessed data
* Database indexing for faster queries
* Lazy loading relationships
* Distributed task processing with Celery
* Docker containerization for consistent deployment

## Development Workflow

1. Create a new branch for each feature or bugfix
2. Write tests before implementing features
3. Ensure all tests pass before creating pull requests
4. Document code with docstrings and update API reference as needed
5. Use pre-commit hooks for code quality checks

## Monitoring and Logging

* Celery task logging for background tasks
* Audit logging for tracking changes to tasks
* Database migration tracking

## License

[MIT License](LICENSE)