from django.contrib import admin
from .models import Order

class OrderAdmin(admin.ModelAdmin):
    fields = ['client_id', 'date_order', 'total']
    list_display = ('id', 'client_id', 'date_order', 'total')
    list_filter = ('client_id', 'date_order', 'total')


admin.site.register(Order, OrderAdmin)
