from django import forms

from .models import UserLotsInput

class UserLotsInputForm(forms.ModelForm):
	class Meta:
		model = UserLotsInput
		fields = [
			# "user_id",
			"number_of_lots"
		]
		# widgets = {
		# 	'number_of_lots': forms.TextInput(attrs={'class': 'myfieldclass'}),
		# }