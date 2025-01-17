from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Client, PaymentRequest, Tariff
from .utils import filter_visible_tariffs


class CustomUserCreationForm(UserCreationForm):
    """Форма регистрации пользователя."""
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    client_type = forms.ChoiceField(
        choices=Client.CLIENT_TYPE_CHOICES, label="Тип клиента"
    )
    contract_number = forms.CharField(
        max_length=50, label="Номер договора", required=False
    )
    tariff = forms.ModelChoiceField(
        queryset=filter_visible_tariffs(Tariff.objects.all()),
        label="Тариф",
        required=False
    )

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            Client.objects.create(
                user=user,
                client_type=self.cleaned_data['client_type'],
                contract_number=self.cleaned_data['contract_number'],
                tariff=self.cleaned_data['tariff']
            )
        return user

    def clean(self):
        cleaned_data = super().clean()
        client_type = cleaned_data.get("client_type")
        contract_number = cleaned_data.get("contract_number")
        tariff = cleaned_data.get("tariff")

        if client_type and not contract_number:
            self.add_error(
                'contract_number',
                "Номер договора обязателен для всех типов клиентов."
            )

        if client_type and not tariff:
            self.add_error(
                'tariff',
                "Выбор тарифа обязателен для всех типов клиентов."
            )

        return cleaned_data


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ('client_type', 'tariff', 'contract_number')
        widgets = {
            'client_type': forms.Select(),
            'tariff': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contract_number'].required = False

    def clean(self):
        cleaned_data = super().clean()
        client_type = cleaned_data.get("client_type")
        contract_number = cleaned_data.get("contract_number")

        if client_type and not contract_number:
            self.add_error('contract_number', "Номер договора обязателен.")

        return cleaned_data


class PaymentRequestForm(forms.ModelForm):
    class Meta:
        model = PaymentRequest
        fields = ['meter_reading']

    def clean_meter_reading(self):
        meter_reading = self.cleaned_data.get('meter_reading')
        if meter_reading < 0:
            raise forms.ValidationError(
                "Показания счетчика не могут быть отрицательными."
            )
        return meter_reading
