from datetime import datetime
from app.models import db
from app.models.user import User, Role


class AuthService:
    def get_user_by_username(self, username):
        """Get user by username"""
        return User.query.filter_by(username=username).first()
    
    def get_user_by_email(self, email):
        """Get user by email"""
        return User.query.filter_by(email=email).first()
    
    def create_user(self, username, email, password, roles=None):
        """
        Create a new user
        
        Args:
            username (str): Username
            email (str): Email address
            password (str): Plain text password (will be hashed)
            roles (list): List of role names to assign (default: ['user'])
            
        Returns:
            User: Created user object
        """
        user = User(
            username=username,
            email=email
        )
        user.password = password  # This will hash the password
        
        # Assign default role if none provided
        if not roles:
            roles = ['user']
            
        # Get or create roles
        for role_name in roles:
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                role = Role(name=role_name)
                db.session.add(role)
            user.roles.append(role)
        
        db.session.add(user)
        db.session.commit()
        return user
    
    def authenticate_user(self, username, password):
        """
        Authenticate user with username and password
        
        Args:
            username (str): Username
            password (str): Plain text password
            
        Returns:
            User: User object if authentication successful, None otherwise
        """
        user = self.get_user_by_username(username)
        
        if user and user.verify_password(password):
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            return user
            
        return None