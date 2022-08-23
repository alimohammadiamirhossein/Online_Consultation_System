from django_filters import FilterSet
from django_filters import DateFilter
from .models import *


class DoctorFreeTimesFilter(FilterSet):
    def __init__(self, *args, **kwargs):
        super(DoctorFreeTimesFilter, self).__init__(*args, **kwargs)
        self.filters['start_time'].label = 'Start Time'

    start_time = DateFilter(field_name='start_time', lookup_expr='gte')

    class Meta:
        model = DoctorFreeTimes
        fields = ('doctor', 'start_time')