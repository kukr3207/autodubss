from django.shortcuts import render

from .logic.run import executeBNFuturesOrder
from home.forms import UserBNFuturesRelationForm

# Create your views here.
def executeBNFuturesBot(request):
    executeBNFuturesOrder()
    bn_futures_form = UserBNFuturesRelationForm(request.POST or None)
    context = {
        'bn_futures_form':bn_futures_form,
    }	
    return render(request,'home.html',context)

    