import sqlite3
import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
# from ..models.alarm_rule import AlarmRule
# from ..models.alarm_state import AlarmState
# from ..utils.logger import get_logger
from src.models.alarm_rule import AlarmRule
from src.models.alarm_state import AlarmState
from src.utils.logger import get_logger

class StorageService:
    """SQLite-based storage service for alarm rules and states"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = get_logger('StorageService')
        self._create_database()
    
    def _create_database(self):
        """Create database tables if they don't exist"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Alarm rules table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS alarm_rules (
                        rule_id TEXT PRIMARY KEY,
                        device_id TEXT NOT NULL,
                        rule_data TEXT NOT NULL,
                        enabled INTEGER DEFAULT 1,
                        created_at REAL,
                        updated_at REAL
                    )
                ''')
                
                # Alarm states table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS alarm_states (
                        rule_id TEXT PRIMARY KEY,
                        device_id TEXT NOT NULL,
                        state_data TEXT NOT NULL,
                        updated_at REAL,
                        FOREIGN KEY (rule_id) REFERENCES alarm_rules (rule_id)
                    )
                ''')
                
                # Alarm history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS alarm_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        rule_id TEXT NOT NULL,
                        device_id TEXT NOT NULL,
                        alarm_data TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        FOREIGN KEY (rule_id) REFERENCES alarm_rules (rule_id)
                    )
                ''')
                
                # Indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_id ON alarm_rules (device_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_state_device ON alarm_states (device_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_timestamp ON alarm_history (timestamp)')
                
                conn.commit()
                self.logger.info("Database tables created/verified successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to create database: {e}")
            raise
    
    def save_alarm_rule(self, rule: AlarmRule) -> bool:
        """Save or update an alarm rule"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                now = datetime.now().timestamp()
                rule_data = rule.to_json()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO alarm_rules 
                    (rule_id, device_id, rule_data, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, COALESCE((SELECT created_at FROM alarm_rules WHERE rule_id = ?), ?), ?)
                ''', (rule.rule_id, rule.device_id, rule_data, 
                     1 if rule.enabled else 0, rule.rule_id, now, now))
                
                conn.commit()
                self.logger.info(f"Saved alarm rule: {rule.rule_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save alarm rule {rule.rule_id}: {e}")
            return False
    
    def get_alarm_rule(self, rule_id: str) -> Optional[AlarmRule]:
        """Get an alarm rule by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT rule_data FROM alarm_rules WHERE rule_id = ?', (rule_id,))
                result = cursor.fetchone()
                
                if result:
                    return AlarmRule.from_json(result[0])
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get alarm rule {rule_id}: {e}")
            return None
    
    def get_all_alarm_rules(self, device_id: Optional[str] = None) -> List[AlarmRule]:
        """Get all alarm rules, optionally filtered by device_id"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if device_id:
                    cursor.execute('SELECT rule_data FROM alarm_rules WHERE device_id = ? AND enabled = 1', 
                                 (device_id,))
                else:
                    cursor.execute('SELECT rule_data FROM alarm_rules WHERE enabled = 1')
                
                results = cursor.fetchall()
                return [AlarmRule.from_json(row[0]) for row in results]
                
        except Exception as e:
            self.logger.error(f"Failed to get alarm rules: {e}")
            return []
    
    def delete_alarm_rule(self, rule_id: str) -> bool:
        """Delete an alarm rule and its state"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM alarm_rules WHERE rule_id = ?', (rule_id,))
                cursor.execute('DELETE FROM alarm_states WHERE rule_id = ?', (rule_id,))
                
                conn.commit()
                self.logger.info(f"Deleted alarm rule: {rule_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to delete alarm rule {rule_id}: {e}")
            return False
    
    def save_alarm_state(self, state: AlarmState) -> bool:
        """Save or update an alarm state"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                state_data = state.to_json()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO alarm_states 
                    (rule_id, device_id, state_data, updated_at)
                    VALUES (?, ?, ?, ?)
                ''', (state.rule_id, state.device_id, state_data, 
                     datetime.now().timestamp()))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save alarm state {state.rule_id}: {e}")
            return False
    
    def get_alarm_state(self, rule_id: str) -> Optional[AlarmState]:
        """Get an alarm state by rule ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT state_data FROM alarm_states WHERE rule_id = ?', (rule_id,))
                result = cursor.fetchone()
                
                if result:
                    return AlarmState.from_json(result[0])
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get alarm state {rule_id}: {e}")
            return None
    
    def get_all_alarm_states(self) -> List[AlarmState]:
        """Get all alarm states"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT state_data FROM alarm_states')
                results = cursor.fetchall()
                
                return [AlarmState.from_json(row[0]) for row in results]
                
        except Exception as e:
            self.logger.error(f"Failed to get alarm states: {e}")
            return []
    
    def save_alarm_history(self, rule_id: str, device_id: str, alarm_data: Dict[str, Any]) -> bool:
        """Save alarm trigger to history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO alarm_history 
                    (rule_id, device_id, alarm_data, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (rule_id, device_id, json.dumps(alarm_data), 
                     datetime.now().timestamp()))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save alarm history: {e}")
            return False
    
    def cleanup_old_history(self, retention_days: int = 30) -> bool:
        """Clean up old alarm history"""
        try:
            cutoff_time = (datetime.now() - timedelta(days=retention_days)).timestamp()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM alarm_history WHERE timestamp < ?', (cutoff_time,))
                deleted_count = cursor.rowcount
                
                conn.commit()
                self.logger.info(f"Cleaned up {deleted_count} old alarm history records")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup alarm history: {e}")
            return False