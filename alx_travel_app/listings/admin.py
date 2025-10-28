from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("booking_reference", "tx_ref", "amount", "status", "created_at")
    readonly_fields = ("created_at", "updated_at")

# Register your models here.
