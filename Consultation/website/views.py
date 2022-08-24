import datetime

from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DeleteView
from django.views.generic import ListView, FormView

from website.forms import DoctorCreationForm, CustomUserCreationForm, PatientCreationForm, CreateTicketForm
from website.forms import DoctorFreeTimesForm
from website.models import DoctorUser, PatientUser, DoctorFreeTimes, Ticket
from .filters import DoctorFreeTimesFilter
from .forms import TransactionForm
from .models import Transaction
from .models import Visit
from .zp import Zarinpal, ZarinpalError


# class DoctorFreeTimeForm(ModelForm):
#     doctor =


class HomePageView(ListView):
    model = DoctorFreeTimes
    template_name = 'website/home.html'
    filter_free_times = DoctorFreeTimesFilter()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = self.filter_free_times
        return context

    def get_queryset(self):
        my_filter = DoctorFreeTimesFilter(self.request.GET, queryset=DoctorFreeTimes.objects.all())
        return my_filter.qs


def doctor_signup(request):
    if request.method == "POST":
        user_form = CustomUserCreationForm(request.POST)
        doctor_form = DoctorCreationForm(request.POST, request.FILES)
        context = {
            "user_form": user_form, "doctor_form": doctor_form,
        }

        if user_form.is_valid() and doctor_form.is_valid():
            with transaction.atomic():
                user = user_form.save()
                doctor: DoctorUser = doctor_form.save(commit=False)
                doctor.user = user
                doctor.save()
                login(request, user)
                object_list = DoctorFreeTimes.objects.all()
                return render(
                    request,
                    'website/home.html',
                    context={
                        'object_list': object_list,
                        "message": "you have successfully signed up for online consultant as Doctor"
                    }
                )
    else:
        user_form = CustomUserCreationForm()
        doctor_form = DoctorCreationForm()
        context = {"user_form": user_form, "doctor_form": doctor_form}

    return render(request, 'website/doctor_signup.html', context=context)


def patient_signup(request):
    if request.method == "POST":
        user_form = CustomUserCreationForm(request.POST)
        patient_form = PatientCreationForm(request.POST)
        context = {"user_form": user_form, "patient_form": patient_form}
        if user_form.is_valid() and patient_form.is_valid():
            with transaction.atomic():
                user = user_form.save()
                patient: DoctorUser = patient_form.save(commit=False)
                patient.user = user
                patient.save()
                login(request, user)
                return redirect('/')
    else:
        user_form = CustomUserCreationForm()
        patient_form = PatientCreationForm()
        context = {"user_form": user_form, "patient_form": patient_form}

    return render(request, 'website/patient_signup.html', context=context)

