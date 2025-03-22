import time
import logging

logger = logging.getLogger(__name__)

def analyze_file(file_path, metadata):
    """Пример задачи для обработки файла"""
    try:
        logger.info(f"Starting analysis of {file_path}")
        # Имитация длительной обработки
        time.sleep(2)
        
        # Возвращаем пример результата
        return {
            'file': file_path,
            'status': 'completed',
            'findings': []
        }
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        raise