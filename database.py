import os
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="planner.db"):
        """Initialize database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """Get a database connection."""
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        """Create the tasks table if it doesn't exist."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    due_date TEXT,
                    category TEXT DEFAULT 'Other',
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def add_task(self, user_id: int, description: str, due_date: str = None, category: str = "Other") -> int:
        """Add a new task for a user."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO tasks (user_id, description, due_date, category)
                VALUES (?, ?, ?, ?)
            """, (user_id, description, due_date, category))
            
            task_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Task added: ID={task_id}, User={user_id}")
            return task_id
        except Exception as e:
            logger.error(f"Error adding task: {e}")
            raise
    
    def get_tasks(self, user_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Get tasks for a user, optionally filtered by status."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if status:
                cursor.execute("""
                    SELECT id, user_id, description, due_date, category, status, created_at, completed_at
                    FROM tasks
                    WHERE user_id = ? AND status = ?
                    ORDER BY due_date ASC, created_at ASC
                """, (user_id, status))
            else:
                cursor.execute("""
                    SELECT id, user_id, description, due_date, category, status, created_at, completed_at
                    FROM tasks
                    WHERE user_id = ?
                    ORDER BY status DESC, due_date ASC, created_at ASC
                """, (user_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            tasks = []
            for row in rows:
                tasks.append({
                    'id': row[0],
                    'user_id': row[1],
                    'description': row[2],
                    'due_date': row[3],
                    'category': row[4],
                    'status': row[5],
                    'created_at': row[6],
                    'completed_at': row[7]
                })
            
            return tasks
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            return []
    
    def get_tasks_by_date(self, user_id: int, date: str) -> List[Dict[str, Any]]:
        """Get tasks for a specific date."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, user_id, description, due_date, category, status, created_at, completed_at
                FROM tasks
                WHERE user_id = ? AND due_date = ?
                ORDER BY status DESC, created_at ASC
            """, (user_id, date))
            
            rows = cursor.fetchall()
            conn.close()
            
            tasks = []
            for row in rows:
                tasks.append({
                    'id': row[0],
                    'user_id': row[1],
                    'description': row[2],
                    'due_date': row[3],
                    'category': row[4],
                    'status': row[5],
                    'created_at': row[6],
                    'completed_at': row[7]
                })
            
            return tasks
        except Exception as e:
            logger.error(f"Error getting tasks by date: {e}")
            return []
    
    def complete_task(self, task_id: int, user_id: int) -> bool:
        """Mark a task as complete."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE tasks
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ? AND status = 'pending'
            """, (task_id, user_id))
            
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            return affected > 0
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            return False
    
    def delete_task(self, task_id: int, user_id: int) -> bool:
        """Delete a task."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM tasks
                WHERE id = ? AND user_id = ?
            """, (task_id, user_id))
            
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            return affected > 0
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return False
    
    def get_stats(self, user_id: int) -> Dict[str, Any]:
        """Get task statistics for a user."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Total, pending, completed
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM tasks
                WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            stats = {
                'total': row[0] or 0,
                'pending': row[1] or 0,
                'completed': row[2] or 0,
                'by_category': {}
            }
            
            # Tasks by category
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM tasks
                WHERE user_id = ?
                GROUP BY category
                ORDER BY count DESC
            """, (user_id,))
            
            for row in cursor.fetchall():
                stats['by_category'][row[0]] = row[1]
            
            conn.close()
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'total': 0, 'pending': 0, 'completed': 0, 'by_category': {}}
    
    def clear_all_tasks(self, user_id: int) -> bool:
        """Clear all tasks for a user (dangerous operation)."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM tasks WHERE user_id = ?", (user_id,))
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            return affected > 0
        except Exception as e:
            logger.error(f"Error clearing tasks: {e}")
            return False
