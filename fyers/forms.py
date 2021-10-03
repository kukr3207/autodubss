from django import forms

from .models import UserBankniftyFyersRelation, UserCrudeoilFyersRelation, UserIntradayStraddleRelation, UserBNOptionsBuyingFyersRelation

class UserBankniftyFyersRelationForm(forms.ModelForm):
	class Meta:
		model = UserBankniftyFyersRelation
		fields = [
			# "user_id",
			# "fyers_id",
			# "fyers_password",
			# "fyers_pan_dob",
			"number_of_lots",
			# "stock",	
		]

class UserCrudeoilFyersRelationForm(forms.ModelForm):
	class Meta:
		model = UserCrudeoilFyersRelation
		fields = [
			# "user_id",
			# "fyers_id",
			# "fyers_password",
			# "fyers_pan_dob",
			"number_of_lots",
			# "stock",	
		]

class UserBNOptionsBuyingFyersRelationForm(forms.ModelForm):
	class Meta:
		model = UserBNOptionsBuyingFyersRelation
		fields = [
			# "user_id",
			# "fyers_id",
			# "fyers_password",
			# "fyers_pan_dob",
			# "stock",
			"number_of_lots",
			# "stock",	
		]