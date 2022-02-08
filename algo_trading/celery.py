import os

import bn_options.tasks
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE",'algo_trading.settings')

app = Celery('algo_trading')
app.config_from_object('django.conf:settings',namespace='CELERY')

# defining when to run a task
app.conf.beat_schedule= {
        'test_funk_30secs_random_name': {
        'task': 'live_data.tasks.test_funk',
        'schedule': 30
    }
}

app.autodiscover_tasks()