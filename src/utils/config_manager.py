"""
Database configuration manager for Song Recommendation System.
Provides utilities for managing database connections and sessions.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
import os
from dotenv import load_dotenv
from src.utils.settings import DB_PATH

# Load environment variables
load_dotenv()

# Base class for all models
Base = declarative_base()

class DatabaseManager:
    """Database manager class for handling database connections and sessions."""
    
    def __init__(self, database_url=None):
        """Initialize the database manager with a database URL."""
        # Use DB_PATH from settings as the default
        if database_url:
            self.database_url = database_url
        else:
            # Create SQLite URL from path in DB_PATH
            self.database_url = f"sqlite:///{DB_PATH}"
        
        self.engine = None
        self.session_factory = None
        self.Session = None
    
    def setup(self):
        """Set up the database engine and session factory."""
        # Create engine
        self.engine = create_engine(self.database_url, echo=False)
        
        # Create session factory
        self.session_factory = sessionmaker(bind=self.engine)
        
        # Create scoped session
        self.Session = scoped_session(self.session_factory)
        
        return self
    
    def create_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(self.engine)
        print("Database tables created successfully!")
    
    def drop_tables(self):
        """Drop all tables from the database."""
        Base.metadata.drop_all(self.engine)
        print("Database tables dropped successfully!")
    
    def get_session(self):
        """Get a new session."""
        if not self.Session:
            self.setup()
        return self.Session()
    
    def close_session(self, session):
        """Close a session."""
        session.close()
    
    def close_all_sessions(self):
        """Close all sessions."""
        if self.Session:
            self.Session.remove()


# Create a singleton instance with the default database path
db_manager = DatabaseManager()

# Convenience function to get a session
def get_db_session(database_url=None):
    """
    Get a database session.
    
    Args:
        database_url (str, optional): Custom database URL to override default
        
    Returns:
        SQLAlchemy session
    """
    if database_url:
        # Create a new manager with the provided URL
        custom_manager = DatabaseManager(database_url)
        custom_manager.setup()
        return custom_manager.get_session()
    
    return db_manager.get_session()


# For use in other modules
def get_engine():
    """Get the database engine."""
    if not db_manager.engine:
        db_manager.setup()
    return db_manager.engine


# Initialize database
def init_db():
    """Initialize the database with any initial data."""
    db_manager.setup()
    db_manager.create_tables()
    
    # Add any initial data here if needed
    session = db_manager.get_session()
    # Example: session.add(User(username="admin", email="admin@example.com"))
    session.commit()
    db_manager.close_session(session)
    print("Database initialized successfully!")


if __name__ == "__main__":
    # This will run if the script is executed directly
    init_db()