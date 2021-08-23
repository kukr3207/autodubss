# runapscheduler.py
import logging

from django.conf import settings

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler import util

from .main import StockMarket
from .crudeoil import CrudeoilBot

logger = logging.getLogger(__name__)


def my_job(a):
  # Your job processing logic here...
  print(a)
  print("@@@@@@@@@@@@@@@@%$$$$$$$$$$$$$$$$$")
  pass

# def executeTrade(access_token, fyers_id,fyers_password,fyers_pan_dob,number_of_lots,user,stock,form_obj):
def executeBankniftyTrade(access_token,number_of_lots,user,stock,form_obj):
    print("hiiiiiiiiiqwweeeertyuioertyuertyuertyu")
    # algo_obj = StockMarket(access_token,fyers_id,fyers_password,fyers_pan_dob)
    algo_obj = StockMarket(access_token)
    order_id_1, order_id_2 = algo_obj.run(number_of_lots,user)
    form_obj.stock = stock
    form_obj.order_id_1 = str(order_id_1)
    form_obj.order_id_2 = str(order_id_2)
    form_obj.save() # Save the final "real form" to the DB

def executeCrudeoilTrade(access_token,number_of_lots,user,stock,form_obj):
    # algo_obj = StockMarket(access_token,fyers_id,fyers_password,fyers_pan_dob)
    algo_obj = CrudeoilBot(access_token)
    order_id_1, order_id_2 = algo_obj.run(number_of_lots,user)
    form_obj.stock = stock
    form_obj.order_id_1 = str(order_id_1)
    form_obj.order_id_2 = str(order_id_2)
    form_obj.save() # Save the final "real form" to the DB

# The `close_old_connections` decorator ensures that database connections, that have become
# unusable or are obsolete, are closed before and after our job has run.
@util.close_old_connections
def delete_old_job_executions(max_age):
  """
  This job deletes APScheduler job execution entries older than `max_age` from the database.
  It helps to prevent the database from filling up with old historical records that are no
  longer useful.
  
  :param max_age: The maximum length of time to retain historical job execution records.
                  Defaults to 7 days.
  """
  DjangoJobExecution.objects.delete_old_job_executions(max_age)

class Command(BaseCommand):
    help = "Runs APScheduler."

    # def handle(self,access_token,fyers_id,fyers_password,fyers_pan_dob,number_of_lots,user,stock,form_obj ,*args, **options):
    def bankniftyScheduler(self,access_token,number_of_lots,user,stock,form_obj ,*args, **options):
        scheduler = BackgroundScheduler({
            'apscheduler.executors.default': {
            'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
            'max_workers': '20'
                },
            'apscheduler.executors.processpool': {
                'type': 'processpool',
                'max_workers': '3'
                },
                'apscheduler.job_defaults.max_instances': '12',
                'misfire_grace_time': 5*60,
                'apscheduler.timezone': settings.TIME_ZONE,
            })
        scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.add_job(
            executeBankniftyTrade,
            'cron',
            # args=[access_token,fyers_id,fyers_password,fyers_pan_dob,number_of_lots,user,stock,form_obj],
            args=[access_token,number_of_lots,user,stock,form_obj],
            hour=17, minute=47, #day_of_week='',
            # id="my_job",  # The `id` assigned to each job MUST be unique
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info("Added job 'my_job'.")

        # scheduler.add_job(
        #     delete_old_job_executions,
        #     args = [19800],
        #     trigger=CronTrigger(
        #         day_of_week="*", hour="14", minute="50"
        #     ),  
        #     id="delete_old_job_executions",
        #     max_instances=1,
        #     replace_existing=True,
        # )
        # logger.info(
        #     "Added weekly job: 'delete_old_job_executions'."
        # )

        try:
            logger.info("Starting scheduler...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully!")

    def crudeoilScheduler(self,access_token,number_of_lots,user,stock,form_obj ,*args, **options):
        scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.add_job(
            executeCrudeoilTrade,
            'cron',
            # args=[access_token,fyers_id,fyers_password,fyers_pan_dob,number_of_lots,user,stock,form_obj],
            args=[access_token,number_of_lots,user,stock,form_obj],
            day_of_week='mon-fri', hour=9, minute=10,
            # id="my_job",  # The `id` assigned to each job MUST be unique
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added job 'my_job'.")

        # scheduler.add_job(
        #     delete_old_job_executions,
        #     trigger=CronTrigger(
        #         day_of_week="*", hour="15", minute="00"
        #     ),  # Midnight on Monday, before start of the next work week.
        #     id="delete_old_job_executions",
        #     max_instances=1,
        #     replace_existing=True,
        # )
        # logger.info(
        #     "Added weekly job: 'delete_old_job_executions'."
        # )

        try:
            logger.info("Starting scheduler...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully!")
