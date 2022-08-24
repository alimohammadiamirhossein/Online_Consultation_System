from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms import ModelForm

from website.models import DoctorUser, PatientUser, DoctorFreeTimes, Ticket


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']


class DoctorCreationForm(ModelForm):
    def __int__(self, *args, **kwargs):
        super(DoctorCreationForm, self).__init__(*args, **kwargs)
        self.fields['national_card_image'].required = False

    class Meta:
        model = DoctorUser
        fields = ['phone_number', 'gmc_number', 'national_id', 'national_card_image']


class DoctorFreeTimesForm(ModelForm):
    class Meta:
        model = DoctorFreeTimes
        fields = ['start_time', 'duration', 'price']


class PatientCreationForm(ModelForm):
    class Meta:
        model = PatientUser
        fields = ['phone_number', 'national_id']


class TransactionForm(forms.Form):
    description = forms.CharField(max_length=200, required=True)
    mobile = forms.CharField(max_length=11, required=False)
    email = forms.EmailField(required=False)
    amount = forms.IntegerField(required=True)


class CreateTicketForm(ModelForm):
    class Meta:
        model = Ticket
        fields = ['request']
