import logging
import os
import yaml
from datetime import datetime

def setup_logger(config_path="config/config.yaml"):
    """Setup logging configuration"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        log_config = config.get('logging', {})
        log_file = log_config.get('file', 'logs/app.log')
        log_level = log_config.get('level', 'INFO')
        log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        logger = logging.getLogger('AlarmService')
        logger.info(f"Logger initialized at {datetime.now()}")
        return logger
        
    except Exception as e:
        # Fallback logging if config fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger('AlarmService')
        logger.error(f"Failed to setup logger from config: {e}")
        return logger

def get_logger(name):
    """Get a logger with the specified name"""
    return logging.getLogger(name)