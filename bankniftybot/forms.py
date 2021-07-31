from django import forms

from .models import UserLotsInput

class UserLotsInputForm(forms.ModelForm):
	class Meta:
		model = UserLotsInput
		fields = [
			# "user_id",
			"fyers_id",
			"fyers_password",
			"fyers_pan_dob",
			"number_of_lots",
			"stock",
			
		]
		# widgets = {
		# 	'number_of_lots': forms.TextInput(attrs={'class': 'myfieldclass'}),
		# }