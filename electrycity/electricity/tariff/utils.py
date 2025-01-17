from django.db.models import QuerySet
from .models import Tariff

def filter_visible_tariffs(queryset: QuerySet) -> QuerySet:
    return queryset.filter(is_hidden=False)
