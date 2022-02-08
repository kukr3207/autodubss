from django.db import models

# Create your models here.
class BNFuturesBotOrders(models.Model):
    dummy_id = models.IntegerField(default=1)
    order_value_1 = models.IntegerField()
    side_1 = models.IntegerField()
    difference_1 = models.IntegerField()
    order_value_2 = models.IntegerField()
    side_2 = models.IntegerField()
    difference_2 = models.IntegerField()