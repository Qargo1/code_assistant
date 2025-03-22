import json
from datetime import datetime
from jinja2 import Template
import matplotlib.pyplot as plt

class ReportGenerator:
    def __init__(self):
        self.report_template = """
        # System Report ({{timestamp}})
        
        ## Statistics
        - Processed jobs: {{metrics.jobs_processed}}
        - Average job duration: {{metrics.avg_job_duration|round(2)}}s
        - Vector DB size: {{metrics.vector_db_size}}
        
        ## Top Error Types
        {% for error in metrics.top_errors %}
        - {{error.type}}: {{error.count}}
        {% endfor %}
        """

    def generate_daily_report(self, metrics):
        """Генерация Markdown-отчета"""
        template = Template(self.report_template)
        return template.render(
            timestamp=datetime.now().isoformat(),
            metrics=metrics
        )

    def create_plots(self, metrics_data, output_dir="reports"):
        """Создание графиков для отчета"""
        # График использования CPU
        plt.plot(metrics_data['timestamps'], metrics_data['cpu'])
        plt.savefig(f"{output_dir}/cpu_usage.png")
        
        # График обработки задач
        plt.bar(metrics_data['jobs'].keys(), metrics_data['jobs'].values())
        plt.savefig(f"{output_dir}/jobs_processed.png")