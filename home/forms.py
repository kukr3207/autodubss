from django import forms

from .models import UserBNFuturesRelation, UserBNOptionsRelation

class UserBNFuturesRelationForm(forms.ModelForm):
    number_of_lots = forms.IntegerField(min_value=1)

    class Meta:
        model = UserBNFuturesRelation
        fields = ["number_of_lots"]

class UserBNOptionsRelationForm(forms.ModelForm):
    number_of_lots = forms.IntegerField(min_value=1)

    class Meta:
        model = UserBNOptionsRelation
        fields = ["number_of_lots"]
