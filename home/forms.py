from django import forms

from .models import UserBNFuturesRelation

class UserBNFuturesRelationForm(forms.ModelForm):
	class Meta:
		model = UserBNFuturesRelation
		fields = [
			"number_of_lots",
		]
