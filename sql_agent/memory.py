"""
Memory module for SQLAgent to maintain context across interactions.
"""
import time
from typing import Dict, List, Any, Optional
import json
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)


class Memory:
    """
    Memory storage for the SQL Agent to maintain context across interactions.
    
    Features:
    - In-memory storage with configurable TTL (time-to-live)
    - Persistent storage to disk
    - Retrieval by similarity or recency
    """
    
    def __init__(self, ttl: int = 3600, persistence_path: Optional[str] = None):
        """
        Initialize the memory module.
        
        Args:
            ttl: Time-to-live for memory entries in seconds
            persistence_path: Path to save persistent memory
        """
        self.ttl = ttl
        self.persistence_path = persistence_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "data", 
            "memory.json"
        )
        
        # Initialize memory storage
        self.memory: Dict[str, List[Dict[str, Any]]] = {}
        
        # Load any persistent memory
        self._load_from_disk()
        
        logger.info("Memory module initialized")
    
    def add(self, category: str, item: Any, metadata: Optional[Dict[str, Any]] = None):
        """
        Add an item to memory.
        
        Args:
            category: Category to store the item under
            item: The item to store
            metadata: Optional metadata about the item
        """
        if category not in self.memory:
            self.memory[category] = []
        
        # Create memory entry
        entry = {
            "timestamp": time.time(),
            "content": item,
            "metadata": metadata or {}
        }
        
        self.memory[category].append(entry)
        logger.debug(f"Added item to memory category '{category}'")
        
        # Persist memory to disk if path is configured
        if self.persistence_path:
            self._save_to_disk()
    
    def get(self, category: str, n: int = 5, filter_func=None) -> List[Dict[str, Any]]:
        """
        Get recent items from a memory category.
        
        Args:
            category: Category to retrieve from
            n: Maximum number of items to retrieve
            filter_func: Optional function to filter memory items
            
        Returns:
            List of memory items
        """
        if category not in self.memory:
            return []
        
        # Get all items from category
        items = self.memory[category]
        
        # Filter expired items
        current_time = time.time()
        items = [item for item in items if current_time - item["timestamp"] <= self.ttl]
        
        # Apply custom filter if provided
        if filter_func:
            items = [item for item in items if filter_func(item)]
        
        # Sort by recency (newest first)
        items.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return items[:n]
    
    def clear(self, category: Optional[str] = None):
        """
        Clear memory items.
        
        Args:
            category: Specific category to clear, or None to clear all
        """
        if category:
            if category in self.memory:
                self.memory[category] = []
                logger.info(f"Cleared memory category '{category}'")
        else:
            self.memory = {}
            logger.info("Cleared all memory")
        
        # Update persistent storage
        if self.persistence_path:
            self._save_to_disk()
    
    def _save_to_disk(self):
        """Save memory to disk."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.persistence_path), exist_ok=True)
            
            with open(self.persistence_path, 'w') as f:
                json.dump(self.memory, f)
            logger.debug("Memory saved to disk")
        except Exception as e:
            logger.error(f"Failed to save memory to disk: {e}")
    
    def _load_from_disk(self):
        """Load memory from disk."""
        if os.path.exists(self.persistence_path):
            try:
                with open(self.persistence_path, 'r') as f:
                    self.memory = json.load(f)
                logger.info("Memory loaded from disk")
            except Exception as e:
                logger.error(f"Failed to load memory from disk: {e}")
                self.memory = {}
