from celery import shared_task

@shared_task
def test_funk():
    print("test_funk")