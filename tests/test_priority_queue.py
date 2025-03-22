import pytest
from unittest.mock import Mock
from core.queue.priority_queue import PriorityAnalysisQueue
import redis

@pytest.fixture
def queue():
    return PriorityAnalysisQueue()

def test_add_task_to_correct_queue(queue):
    test_metadata = {
        'dependencies': 5,
        'change_frequency': 0.8,
        'complexity': 0.9
    }
    
    job_id = queue.add_task("/src/main.py", test_metadata)
    assert job_id is not None
    assert queue.high_priority.count > 0

def test_priority_calculation(queue):
    test_cases = [
        ({'dependencies': 10, 'change_frequency': 1.0, 'complexity': 1.0}, 'high'),
        ({'dependencies': 2, 'change_frequency': 0.5, 'complexity': 0.3}, 'medium'),
        ({'dependencies': 0, 'change_frequency': 0.1, 'complexity': 0.1}, 'low')
    ]
    
    for metadata, expected in test_cases:
        queue = queue._determine_priority(metadata)
        assert expected in queue.name

def test_redis_connection():
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        assert r.ping() == True
    except redis.exceptions.ConnectionError:
        pytest.fail("Could not connect to Redis")