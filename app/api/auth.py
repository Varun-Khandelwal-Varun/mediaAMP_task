from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from pydantic import BaseModel, EmailStr, validator
from app.models import db
from app.models.user import User
from app.services.auth_service import AuthService
from app import limiter

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()

# Input validation models
class RegisterUserModel(BaseModel):
    username: str
    email: EmailStr
    password: str
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
    @validator('username')
    def username_check(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        return v


class LoginUserModel(BaseModel):
    username: str
    password: str


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("10 per hour")
def register():
    """
    Register a new user
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: User
          properties:
            username:
              type: string
              description: The user's username
            email:
              type: string
              description: The user's email
            password:
              type: string
              description: The user's password
    responses:
      201:
        description: User successfully created
      400:
        description: Invalid input
      409:
        description: User already exists
    """
    try:
        data = request.get_json()
        user_data = RegisterUserModel(**data)
        
        if auth_service.get_user_by_username(user_data.username):
            return jsonify({"message": "Username already exists"}), 409
        
        if auth_service.get_user_by_email(user_data.email):
            return jsonify({"message": "Email already exists"}), 409
            
        user = auth_service.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password
        )
        
        return jsonify({
            "message": "User registered successfully",
            "id": user.id,
            "username": user.username
        }), 201
        
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("20 per hour")
def login():
    """
    User login endpoint
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: UserLogin
          properties:
            username:
              type: string
              description: The user's username
            password:
              type: string
              description: The user's password
    responses:
      200:
        description: Login successful
      401:
        description: Invalid credentials
    """
    try:
        data = request.get_json()
        user_data = LoginUserModel(**data)
        
        user = auth_service.authenticate_user(user_data.username, user_data.password)
        if not user:
            return jsonify({"message": "Invalid credentials"}), 401
            
        access_token = create_access_token(identity=user.id)
        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "username": user.username
        }), 200
        
    except ValueError as e:
        return jsonify({"message": str(e)}), 400