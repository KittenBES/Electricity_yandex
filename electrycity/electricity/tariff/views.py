from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, FormView, CreateView
from django.views import View
from django.shortcuts import get_object_or_404, render, redirect
from django.db import transaction
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import (
    ClientForm, CustomUserCreationForm,
    ProfileEditForm, PaymentRequestForm
)
from .models import Client, PaymentRequest, Tariff
from .utils import filter_visible_tariffs


class TariffListView(ListView):
    model = Tariff
    template_name = 'tariff/index.html'
    paginate_by = 5

    def get_queryset(self):
        queryset = super().get_queryset()
        return filter_visible_tariffs(queryset)


class RegisterView(View):
    """Представление регистрации пользователя."""
    def get(self, request, *args, **kwargs):
        form = CustomUserCreationForm()
        return render(
            request, 'registration/registration_form.html', {'form': form}
        )

    def post(self, request, *args, **kwargs):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('tariff:index')
        return render(
            request, 'registration/registration_form.html', {'form': form}
        )


class ProfileView(ListView):
    model = PaymentRequest
    template_name = 'tariff/profile.html'
    context_object_name = 'payment_requests'
    paginate_by = 3

    def get_queryset(self):
        user = get_object_or_404(
            User, username=self.kwargs['username']
        )
        PaymentRequest.objects.update_overdue_status()

        queryset = user.client.payment_requests.select_related(
            'client__tariff'
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(
            User, username=self.kwargs['username']
        )
        context['profile'] = user
        context['client'] = user.client
        return context


class EditProfileView(LoginRequiredMixin, FormView):
    template_name = 'tariff/user.html'
    form_class = ProfileEditForm
    client_form_class = ClientForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        client, created = Client.objects.get_or_create(user=user)
        if 'client_form' not in context:
            context['client_form'] = self.client_form_class(
                instance=client, prefix='client'
            )
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        user = self.request.user
        client, created = Client.objects.get_or_create(user=user)
        client_form = self.client_form_class(
            request.POST, instance=client, prefix='client'
        )

        if form.is_valid() and client_form.is_valid():
            return self.form_valid(form, client_form)
        else:
            return self.form_invalid(form, client_form)

    def form_valid(self, form, client_form):
        with transaction.atomic():
            form.save()
            client_form.save()
        messages.success(
            self.request, 'Профиль успешно обновлен.'
        )
        return super().form_valid(form)

    def form_invalid(self, form, client_form):
        messages.error(
            self.request,
            'Пожалуйста, исправьте ошибки в форме.'
        )
        return self.render_to_response(
            self.get_context_data(form=form, client_form=client_form)
        )

    def get_success_url(self):
        return reverse_lazy(
            'tariff:profile', kwargs={'username': self.request.user.username}
        )

    def get_object(self, queryset=None):
        return self.request.user


class CreatePaymentRequestView(LoginRequiredMixin, CreateView):
    """Представление для создания заявки на оплату."""
    model = PaymentRequest
    form_class = PaymentRequestForm
    template_name = 'tariff/create_payment_request.html'
    success_url = reverse_lazy('tariff:profile')

    def dispatch(self, request, *args, **kwargs):
        """
        Проверяет, является ли пользователь клиентом,
        прежде чем разрешить создание заявки на оплату.
        """
        if not hasattr(request.user, 'client'):
            messages.error(
                request,
                "Извините, только клиенты могут создавать заявки на оплату."
            )
            return redirect(
                'tariff:profile', username=request.user.username
            )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """
        Устанавливает клиента для заявки на оплату перед сохранением.
        """
        form.instance.client = self.request.user.client
        messages.success(
            self.request, 'Заявка на оплату успешно создана.'
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'tariff:profile', kwargs={'username': self.request.user.username}
        )


@login_required
def mark_payment_request_paid(request, request_id):
    """Помечает заявку на оплату как оплаченную."""
    payment_request = get_object_or_404(
        PaymentRequest.objects.select_related('client__user'), pk=request_id
    )

    if payment_request.client.user != request.user:
        messages.error(
            request, "Вы не можете изменять чужие заявки."
        )
        return redirect(
            'tariff:profile', username=request.user.username
        )

    payment_request.is_paid = True
    payment_request.save()
    PaymentRequest.objects.update_overdue_status()
    messages.success(
        request, "Заявка на оплату помечена как оплаченная."
    )
    return redirect('tariff:profile', username=request.user.username)
