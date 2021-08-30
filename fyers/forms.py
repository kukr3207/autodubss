from django import forms

from .models import UserBankniftyFyersRelation, UserCrudeoilFyersRelation, UserIntradayStraddleRelation

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

class UserIntradayStraddleRelationForm(forms.ModelForm):
	class Meta:
		model = UserIntradayStraddleRelation
		fields = [
			# "user_id",
			# "fyers_id",
			# "fyers_password",
			# "fyers_pan_dob",
			"stock",
			"number_of_lots",
			# "stock",	
		]