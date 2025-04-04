from flask_script import Manager
from flask_migrate import MigrateCommand
from app import app, db  # Ensure you import your app and db from your main application file

manager = Manager(app)