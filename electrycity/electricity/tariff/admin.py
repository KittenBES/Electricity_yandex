from django.contrib import admin
from django.utils.html import format_html

from .models import Tariff, Client, PaymentRequest


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    """Админ-панель для модели Tariff."""
    list_display = (
        'name', 'description', 'payment_method',
        'price_per_kwh', 'fixed_payment', 'is_hidden'
    )
    list_filter = ('payment_method',)
    list_editable = ('is_hidden',)
    search_fields = ('name', 'description')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Админ-панель для модели Client."""
    list_display = ('user', 'client_type', 'tariff_link')
    list_filter = ('client_type', 'tariff')
    search_fields = (
        'user__username', 'user__first_name', 'user__last_name'
    )

    def tariff_link(self, obj):
        """Создает ссылку на связанный объект Tariff в админ-панели."""
        if obj.tariff:
            url = f"/admin/tariff/tariff/{obj.tariff.pk}/change/"
            return format_html(f'<a href="{url}">{obj.tariff}</a>')
        return "Нет тарифа"
    tariff_link.short_description = "Тариф"


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    """Админ-панель для модели PaymentRequest."""
    list_display = (
        'client', 'meter_reading', 'request_date',
        'payment_due_date', 'amount_due', 'is_paid',
        'is_overdue', 'paid_status'
    )
    list_filter = (
        'is_paid', 'is_overdue', 'request_date', 'payment_due_date'
    )
    search_fields = (
        'client__user__username', 'client__user__first_name',
        'client__user__last_name'
    )
    list_editable = ('is_paid', 'is_overdue')

    def paid_status(self, obj):
        """Отображает статус оплаты в удобном виде."""
        if obj.is_paid:
            return format_html(
                '<span style="color: green;">✔ Оплачено</span>'
            )
        elif obj.is_overdue:
            return format_html(
                '<span style="color: red;">✘ Просрочено</span>'
            )
        else:
            return format_html(
                '<span style="color: orange;">- Не оплачено</span>'
            )
    paid_status.short_description = "Статус оплаты"

    list_display_links = ('client', 'meter_reading')
