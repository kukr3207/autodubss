from django import forms

from .models import UserBNFuturesRelation, UserBNOptionsRelation

class UserBNFuturesRelationForm(forms.ModelForm):
	class Meta:
		model = UserBNFuturesRelation
		fields = [
			"number_of_lots",
		]

class UserBNOptionsRelationForm(forms.ModelForm):
	class Meta:
		model = UserBNOptionsRelation
		fields = [
			"number_of_lots",
		]