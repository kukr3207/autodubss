from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Prints all book titles in the database'

    def handle(self, *args, **options):
        try:
            # from fyers.crudeoil_cron import executeCrudeoilOrders
            # executeCrudeoilOrders()
            from fyers.banknifty_cron import executeBankniftyOrders
            executeBankniftyOrders()		
            return "Scheduler ran successfully"
        except Exception as e:
            print(e)
            return "Problem in cron job"
        return "did not even enter try or except in Scheduler"