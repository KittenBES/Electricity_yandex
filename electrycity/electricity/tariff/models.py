from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from abc import ABC, abstractmethod
from django.db.models import Q


class TimestampedModel(models.Model):
    """Абстрактный класс с датой и временем создания объекта."""
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата и время создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Дата и время изменения"
    )

    class Meta:
        abstract = True


class PaymentCalculationStrategy(ABC):
    """Абстрактный класс стратегии расчета стоимости."""
    @abstractmethod
    def calculate(self, meter_reading, tariff):
        """Рассчитывает стоимость."""
        pass


class PerKWhCalculationStrategy(PaymentCalculationStrategy):
    """Стратегия расчета по киловатт-часам."""
    def calculate(self, meter_reading, tariff):
        """Рассчитывает стоимость."""
        return meter_reading * tariff.price_per_kwh


class FixedPaymentCalculationStrategy(PaymentCalculationStrategy):
    """Стратегия расчета с фиксированным платежом."""
    def calculate(self, meter_reading, tariff):
        """Рассчитывает стоимость."""
        return tariff.fixed_payment


class PaymentCalculationStrategyFactory:
    """Фабрика стратегий расчета."""
    @staticmethod
    def get_strategy(payment_method):
        """Возвращает стратегию расчета по методу оплаты."""
        if payment_method == 'per_kwh':
            return PerKWhCalculationStrategy()
        elif payment_method == 'fixed':
            return FixedPaymentCalculationStrategy()
        else:
            raise ValueError(
                f"Неизвестный метод оплаты: {payment_method}"
            )


class Tariff(TimestampedModel):
    """Модель тарифа."""
    PAYMENT_CHOICES = (
        ('per_kwh', 'Цена за кВтч'),
        ('fixed', 'Фиксированный платеж'),
    )

    name = models.CharField(
        max_length=255, verbose_name="Название тарифа"
    )
    description = models.TextField(verbose_name="Описание тарифа")
    price_per_kwh = models.DecimalField(
        max_digits=10, decimal_places=2, null=True,
        blank=True, verbose_name="Цена за кВтч"
    )
    fixed_payment = models.DecimalField(
        max_digits=10, decimal_places=2, null=True,
        blank=True, verbose_name="Фиксированный платеж"
    )
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_CHOICES,
        verbose_name="Метод оплаты"
    )
    is_hidden = models.BooleanField(default=False, verbose_name="Скрыт")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Тариф"
        verbose_name_plural = "Тарифы"
        ordering = ('-created_at',)


class Client(models.Model):
    """Модель клиента."""
    CLIENT_TYPE_CHOICES = (
        ('individual', 'Физическое лицо'),
        ('legal', 'Юридическое лицо'),
    )

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, verbose_name="Пользователь",
        related_name="client"
    )
    client_type = models.CharField(
        max_length=20, choices=CLIENT_TYPE_CHOICES,
        verbose_name="Тип клиента"
    )
    tariff = models.ForeignKey(
        Tariff, on_delete=models.SET_NULL, null=True,
        verbose_name="Тариф", related_name="clients"
    )
    contract_number = models.CharField(
        max_length=50, unique=True, verbose_name="Номер договора"
    )

    def __str__(self):
        return (
            f"{self.user.get_full_name() or self.user.username} "
            f"({self.get_client_type_display()})"
        )

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"


class PaymentRequestManager(models.Manager):
    """Менеджер заявок на оплату."""
    def update_overdue_status(self):
        """Обновляет статус просроченных заявок."""
        today = timezone.now().date()
        overdue_requests_q = Q(
            payment_due_date__lt=today, is_paid=False, is_overdue=False
        )
        not_overdue_requests_q = Q(
            payment_due_date__gte=today, is_overdue=True
        ) | Q(is_paid=True, is_overdue=True)

        self.select_related('client__tariff').filter(
            overdue_requests_q
        ).update(is_overdue=True)
        self.filter(not_overdue_requests_q).update(is_overdue=False)


class PaymentRequest(TimestampedModel):
    """Модель заявки на оплату."""
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE,
        verbose_name="Клиент", related_name="payment_requests"
    )
    meter_reading = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Показания счетчика"
    )
    request_date = models.DateField(
        default=timezone.now, verbose_name="Дата заявки"
    )
    payment_due_date = models.DateField(verbose_name="Дата оплаты")
    amount_due = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Сумма к оплате"
    )
    is_paid = models.BooleanField(default=False, verbose_name="Оплачено")
    is_overdue = models.BooleanField(
        default=False, verbose_name="Просрочено"
    )

    objects = PaymentRequestManager()

    def calculate_amount_due(self):
        """Вычисляет сумму к оплате, используя стратегию."""
        return PaymentCalculationStrategyFactory.get_strategy(
            self.client.tariff.payment_method
        ).calculate(self.meter_reading, self.client.tariff)

    def save(self, *args, **kwargs):
        """
        Переопределение метода save для автоматического расчета
        суммы к оплате и установки даты оплаты.
        """
        if not self.pk:
            self.amount_due = self.calculate_amount_due()
            self.payment_due_date = (
                self.request_date + timezone.timedelta(days=30)
            )
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Заявка от {self.client} на {self.request_date}"

    class Meta:
        verbose_name = "Заявка на оплату"
        verbose_name_plural = "Заявки на оплату"
        ordering = ['-created_at']
