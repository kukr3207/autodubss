from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class BNOptionsBotOrders(models.Model):
    dummy_id = models.IntegerField(default=1)
    order_value = models.IntegerField()
    contract = models.CharField(max_length=200, null=True)

class OptionsOrdersDetails(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE) #column name user_id_id
    order_id = models.CharField(max_length=500,null=False)
    code = models.IntegerField()
    message = models.CharField(max_length=1000,null=True)
    is_active = models.IntegerField(default=0)
    def __str__(self):
        return str(self.user_id)