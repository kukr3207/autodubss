from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class UserBNFuturesRelation(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE) #column name user_id_id
    date_added = models.DateTimeField(auto_now_add=True)
    number_of_lots = models.IntegerField()
    fyers_access_token = models.CharField(max_length=1000, null=True)
    def __str__(self):
        return str(self.user_id)

class UserFyersAppRelation(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	date_added = models.DateTimeField(auto_now_add=True)
	fyers_app_id = models.CharField(max_length=300, null=True)
	fyers_app_secretkey = models.CharField(max_length=300, null=True)
	def __str__(self):
		return str(self.user)