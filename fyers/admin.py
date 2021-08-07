from django.contrib import admin
from .models import UserLotsInput

class UserLotsInputAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'date_added', 'number_of_lots') 

# Register your models here.
admin.site.register(UserLotsInput, UserLotsInputAdmin)