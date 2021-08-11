from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User

STOCK_CHOICES = (
    ('BANKNIFTY21AUGFUT', 'BANKNIFTY21AUGFUT'),
)


# Create your models here.

class UserCrudeoilFyersRelation(models.Model):
	user_id = models.ForeignKey(User, on_delete=models.CASCADE)
	date_added = models.DateTimeField(auto_now_add=True)
	stock = models.CharField(max_length=300, null=True, choices=STOCK_CHOICES,)
	number_of_lots = models.IntegerField()
	order_id = models.CharField(max_length=300, null=True)
	value = models.IntegerField(null=True)
	p_and_l = models.IntegerField(null=True)
	fyers_id = models.CharField(max_length=300, null=True)
	fyers_password = models.CharField(max_length=300, null=True)
	fyers_pan_dob = models.CharField(max_length=300, null=True)
	trading_platform = models.CharField(max_length=300, null=True)
	def __str__(self):
		return str(self.user_id)

class UserBankniftyFyersRelation(models.Model):
	user_id = models.ForeignKey(User, on_delete=models.CASCADE)
	date_added = models.DateTimeField(auto_now_add=True)
	stock = models.CharField(max_length=300, null=True, choices=STOCK_CHOICES,)
	number_of_lots = models.IntegerField()
	order_id_1 = models.CharField(max_length=300, null=True)
	order_id_2 = models.CharField(max_length=300, null=True)
	order_closing_type = models.CharField(max_length=50, null=True)
	value = models.IntegerField(null=True)
	p_and_l = models.IntegerField(null=True)
	fyers_id = models.CharField(max_length=300, null=True)
	fyers_password = models.CharField(max_length=300, null=True)
	fyers_pan_dob = models.CharField(max_length=300, null=True)
	trading_platform = models.CharField(max_length=300, null=True)
	def __str__(self):
		return str(self.user_id)

class UserSubscriptionRelation(models.Model):
    user_id = models.OneToOneField(User, on_delete=models.CASCADE)
    subscription_date = models.DateTimeField(auto_now_add=True)

class UserFyersAppRelation(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	date_added = models.DateTimeField(auto_now_add=True)
	fyers_app_id = models.CharField(max_length=300, null=True)
	fyers_app_secretkey = models.CharField(max_length=300, null=True)
	def __str__(self):
		return str(self.user)