from django.contrib import admin
from .models import UserCrudeoilFyersRelation, UserBankniftyFyersRelation, UserSubscriptionRelation, UserFyersAppRelation

class UserBankniftyFyersRelationAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'date_added', 'number_of_lots') 

class UserCrudeoilFyersRelationAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'date_added', 'number_of_lots')

class UserSubscriptionRelationAdmin(admin.ModelAdmin):
    list_display = ('user','last_subscription_date')

class UserFyersAppRelationAdmin(admin.ModelAdmin):
    list_display = ('user','date_added')

# Register your models here.
admin.site.register(UserBankniftyFyersRelation, UserBankniftyFyersRelationAdmin)
admin.site.register(UserCrudeoilFyersRelation, UserCrudeoilFyersRelationAdmin)
admin.site.register(UserSubscriptionRelation, UserSubscriptionRelationAdmin)
admin.site.register(UserFyersAppRelation, UserFyersAppRelationAdmin)
