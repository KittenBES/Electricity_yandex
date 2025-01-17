from django.urls import path

from . import views

app_name = 'tariff'


urlpatterns = [
    path('', views.TariffListView.as_view(), name='index'),
    path(
        'profile/edit/',
        views.EditProfileView.as_view(),
        name='edit_profile'
    ),
    path(
        'profile/<str:username>/',
        views.ProfileView.as_view(),
        name='profile'
    ),
    path(
        'payment_request/create/',
        views.CreatePaymentRequestView.as_view(),
        name='create_payment_request'
    ),
    path(
        'payment_request/<int:request_id>/mark_paid/',
        views.mark_payment_request_paid,
        name='mark_payment_request_paid'
    ),
]
