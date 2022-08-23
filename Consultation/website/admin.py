from django.contrib import admin

from website.models import DoctorUser, DoctorFreeTimes, PatientUser, Visit, Transaction, Ticket

admin.site.register(DoctorFreeTimes)
admin.site.register(PatientUser)
admin.site.register(Visit)
admin.site.register(Transaction)


class IsAnsweredFilter(admin.SimpleListFilter):
    title = 'Is Answered'
    parameter_name = 'is_answered'

    def lookups(self, request, model_admin):
        return (
            ('not_answered', 'Not Answered'),
            ('answered', 'Answered'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'answered':
            return queryset.exclude(response='')
        if self.value() == 'not_answered':
            return queryset.filter(response='')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_filter = ('user', IsAnsweredFilter)
    list_display = ['__str__', 'user', 'is_answered']

    def is_answered(self, obj) -> bool:
        return len(obj.response) > 0

    is_answered.boolean = True


@admin.register(DoctorUser)
class DoctorUserAdmin(admin.ModelAdmin):

    def name(self, obj):
        return f'{obj.user.first_name} {obj.user.last_name}'

    list_display = ['user', 'name', 'gmc_number', 'state', 'national_card_image']

    list_editable = ['state']
