import pytest
from unittest.mock import Mock
from monitoring.metrics import SystemMetrics

def test_metrics_collection():
    metrics = SystemMetrics()
    metrics.cpu_usage.set(50.0)
    assert metrics.cpu_usage._value.get() == 50.0

def test_report_generation():
    from monitoring.reporter import ReportGenerator
    reporter = ReportGenerator()
    test_metrics = {
        'jobs_processed': 120,
        'avg_job_duration': 2.45,
        'vector_db_size': 1500,
        'top_errors': [{'type': 'timeout', 'count': 5}]
    }
    report = reporter.generate_daily_report(test_metrics)
    assert "Processed jobs: 120" in report