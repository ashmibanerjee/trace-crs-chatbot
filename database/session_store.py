"""
Abstract Session Store Interface
Defines the contract for all database implementations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class SessionStore(ABC):
    """Abstract base class for session storage backends"""
    
    @abstractmethod
    async def create_session(self, session_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new session
        
        Args:
            session_id: Unique session identifier
            session_data: Initial session data
            
        Returns:
            Created session data with timestamps
        """
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a session by ID
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found
        """
        pass
    
    @abstractmethod
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update session data
        
        Args:
            session_id: Session identifier
            updates: Partial update data
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        pass
