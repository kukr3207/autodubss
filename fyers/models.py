from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User

STOCK_CHOICES = (
    ('BANKNIFTY21AUGFUT', 'BANKNIFTY21AUGFUT'),
)

OPTIONS_STOCK_CHOICES = (
	("NIFTY-I","NIFTY-I"),
	("BANKNIFTY-I","BANKNIFTY-I"),
)
# Create your models here.

class UserCrudeoilFyersRelation(models.Model):
	user_id = models.ForeignKey(User, on_delete=models.CASCADE)
	date_added = models.DateTimeField(auto_now_add=True)
	stock = models.CharField(max_length=300, null=True, choices=STOCK_CHOICES,)
	number_of_lots = models.IntegerField()
	fyers_access_token = models.CharField(max_length=300, null=True)
	def __str__(self):
		return str(self.user_id)

class UserBankniftyFyersRelation(models.Model):
	user_id = models.ForeignKey(User, on_delete=models.CASCADE)
	date_added = models.DateTimeField(auto_now_add=True)
	stock = models.CharField(max_length=300, null=True, choices=STOCK_CHOICES,)
	number_of_lots = models.IntegerField()
	fyers_access_token = models.CharField(max_length=300, null=True)
	def __str__(self):
		return str(self.user_id)

class UserBNOptionsBuyingFyersRelation(models.Model):
	user_id = models.ForeignKey(User, on_delete=models.CASCADE)
	date_added = models.DateTimeField(auto_now_add=True)
	stock = models.CharField(max_length=300, null=True, choices=STOCK_CHOICES,)
	number_of_lots = models.IntegerField()
	fyers_access_token = models.CharField(max_length=300, null=True)
	def __str__(self):
		return str(self.user_id)

class UserIntradayStraddleRelation(models.Model):
	user_id = models.ForeignKey(User, on_delete=models.CASCADE)
	date_added = models.DateTimeField(auto_now_add=True)
	stock = models.CharField(max_length=300, null=True, choices=OPTIONS_STOCK_CHOICES,)
	number_of_lots = models.IntegerField()
	fyers_access_token = models.CharField(max_length=300, null=True)
	def __str__(self):
		return str(self.user_id)

class UserSubscriptionRelation(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)
    last_subscription_date = models.DateTimeField(null=True)

class UserFyersAppRelation(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	date_added = models.DateTimeField(auto_now_add=True)
	fyers_app_id = models.CharField(max_length=300, null=True)
	fyers_app_secretkey = models.CharField(max_length=300, null=True)
	def __str__(self):
		return str(self.user)