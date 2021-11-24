from django.contrib import admin
from .models import UserBNFuturesRelation, UserFyersAppRelation
# Register your models here.

class UserBNFuturesRelationAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'date_added', 'number_of_lots') 
class UserFyersAppRelationAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_added') 

admin.site.register(UserBNFuturesRelation, UserBNFuturesRelationAdmin)
admin.site.register(UserFyersAppRelation, UserFyersAppRelationAdmin)