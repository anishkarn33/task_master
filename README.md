# TaskMaster API

A comprehensive task management API built with FastAPI, featuring user authentication, CRUD operations for tasks, and advanced filtering capabilities.

## Features

- **User Management**
  - User registration and authentication
  - JWT token-based authentication
  - User profile management

- **Task Management**
  - Create, read, update, delete tasks
  - Task priorities (Low, Medium, High, Urgent)
  - Task statuses (Todo, In Progress, Completed)
  - Due dates and completion tracking
  - Advanced filtering and sorting

- **API Features**
  - RESTful API design
  - Automatic API documentation (Swagger/OpenAPI)
  - CORS support for frontend integration
  - Comprehensive error handling
  - Database migrations with Alembic

## Tech Stack

- **FastAPI** - Modern, fast web framework for APIs
- **SQLAlchemy** - SQL toolkit and ORM
- **PostgreSQL** - Primary database
- **Alembic** - Database migration tool
- **JWT** - Authentication tokens
- **Pydantic** - Data validation using Python type annotations
- **Docker** - Containerization

## Project Structure

```
taskmaster-backend/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── core/            # Core functionality (security, config)
│   ├── models/          # Database models
│   ├── schemas/         # Pydantic schemas
│   └── utils/           # Utility functions
├── tests/               # Test files
├── alembic/            # Database migrations
└── requirements.txt    # Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL
- Docker (optional)

### Local Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd taskmaster-backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your database credentials
```

5. **Set up database**
```bash
# Create PostgreSQL database
createdb taskmaster

# Run migrations
alembic upgrade head
```

6. **Run the application**
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Docker Setup

1. **Run with Docker Compose**
```bash
docker-compose up -d
```

This will start both the API server and PostgreSQL database.

## API Documentation

Once the server is running, you can access:

- **Swagger UI**: `http://localhost:8000/api/docs`
- **ReDoc**: `http://localhost:8000/api/redoc`
- **OpenAPI JSON**: `http://localhost:8000/api/v1/openapi.json`

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/token` - OAuth2 compatible token endpoint

### Users
- `GET /api/v1/users/me` - Get current user info
- `PUT /api/v1/users/me` - Update current user
- `DELETE /api/v1/users/me` - Delete current user

### Tasks
- `GET /api/v1/tasks/` - Get all tasks (with filtering)
- `POST /api/v1/tasks/` - Create new task
- `GET /api/v1/tasks/{id}` - Get specific task
- `PUT /api/v1/tasks/{id}` - Update task
- `DELETE /api/v1/tasks/{id}` - Delete task
- `GET /api/v1/tasks/stats/summary` - Get task statistics

## Usage Examples

### Register a new user
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "full_name": "Test User",
    "password": "password123"
  }'
```

### Login
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

### Create a task
```bash
curl -X POST "http://localhost:8000/api/v1/tasks/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Complete project",
    "description": "Finish the TaskMaster API",
    "priority": "high",
    "due_date": "2024-12-31T23:59:59"
  }'
```

## Testing

Run the test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=app tests/
```

## Database Migrations

Create a new migration:

```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:

```bash
alembic upgrade head
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run tests and ensure they pass
6. Submit a pull request

## License

This project is licensed under the MIT License.