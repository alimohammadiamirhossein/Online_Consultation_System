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


import datetime


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


@login_required(login_url='signup/patient')
def patient_dashboard(request):
    if DoctorUser.objects.filter(user=request.user):
        return render(
            request,
            'website/home.html',
            context={
                "message": "you are not a patient"
            }
        )
    patient = PatientUser.objects.get(user=request.user)
    visits = Visit.objects.filter(patient=patient)
    return render(request, 'website/patient_dashboard.html', context={"name": request.user.get_full_name,
                                                                      "username": request.user.username,
                                                                      "email": request.user.email,
                                                                      "phone": patient.phone_number,
                                                                      "national_id": patient.national_id,
                                                                      "balance": patient.balance,
                                                                      'visits': visits,
                                                                      })


@login_required(login_url='signup/patient')
def doctor_dashboard(request):
    if PatientUser.objects.filter(user=request.user):
        return render(
            request,
            'website/home.html',
            context={
                "message": "you are not a doctor"
            }
        )
    doctor = DoctorUser.objects.get(user=request.user)
    doctor_free_times = DoctorFreeTimes.objects.filter(doctor=doctor).order_by('start_time')
    return render(request, 'website/doctor_dashboard.html', context={"name": request.user.get_full_name,
                                                                     "username": request.user.username,
                                                                     "email": request.user.email,
                                                                     "phone": doctor.phone_number,
                                                                     "national_id": doctor.national_id,
                                                                     "balance": doctor.balance,
                                                                     "gmc_number": doctor.gmc_number,
                                                                     'state': doctor.get_state_display(),
                                                                     'free_times': doctor_free_times,
                                                                     })


class FreeTimeCreateView(View):

    def get(self, request):
        form = DoctorFreeTimesForm()
        content = {
            'form': form,
        }
        return render(request, 'website/add_free_time.html', content)

    def post(self, request):
        form = DoctorFreeTimesForm(request.POST)
        if form.is_valid():
            doctor = DoctorUser.objects.get(user=request.user)
            free_time = DoctorFreeTimes()
            free_time.start_time = form.cleaned_data['start_time']
            free_time.duration = form.cleaned_data['duration']
            free_time.price = form.cleaned_data['price']
            free_time.doctor = doctor
            free_time.save()
            form = DoctorFreeTimesForm()
            return render(request, 'website/add_free_time.html', {
                'message': 'Free Time Added Successfully',
                'form': form,
            })
        return render(request, 'website/add_free_time.html', {
            'message': 'Error When Adding Free Time',
            'form': form,
        })


class DeleteFreeTimeView(DeleteView):
    model = DoctorFreeTimes
    success_url = reverse_lazy('website:doctor_dashboard')


def reserved(request, pk):
    free_time = DoctorFreeTimes.objects.get(id=pk)
    patient = PatientUser.objects.get(user=request.user)
    if patient.balance < free_time.price:
        messages.error(request, "Please increase your balance")
        return redirect('/')
    with transaction.atomic():
        new_balance = patient.balance - free_time.price
        patient.balance = new_balance
        patient.save()
        visit = Visit()
        visit.doctor = free_time.doctor
        visit.patient = patient
        visit.start_time = free_time.start_time
        visit.duration = free_time.duration
        visit.price = free_time.price
        visit.save()
        free_time.delete()
        messages.success(request, "you have reserved an appointment")
        return redirect('/')


def logout_view(request):
    logout(request)
    return redirect('/')


class LoginView(FormView):
    template_name = 'website/login.html'
    form_class = AuthenticationForm
    success_url = '/'

    def form_valid(self, form):
        is_valid = super().form_valid(form)
        if is_valid:
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user:
                login(self.request, user)
            else:
                form.add_error("username", "Username or password is wrong")
                is_valid = False
        return is_valid


'''
 if you want to test youre code on your machine without a real transaction
 you able to use zarinpal sandbox like following code
 if you want use in your product, remove sandbox and replace real mercand and callback url then use it!
'''
zarin_pal = Zarinpal('XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX',
                     'http://127.0.0.1:8000/verify',
                     sandbox=True)


@login_required(login_url='signup/patient')
def payment_gateway(request):
    if DoctorUser.objects.filter(user=request.user):
        return render(
            request,
            'website/home.html',
            context={
                "message": "you are not a patient",
            }
        )
    return render(request, 'website/pay.html')


def pay(request: HttpRequest):
    amount = request.POST.get('amount')
    description = request.POST.get('description')
    email = request.POST.get('email')
    mobile = request.POST.get('mobile')

    try:
        # try to create payment if success get url to redirect it
        redirect_url = zarin_pal.payment_request(amount, description, mobile=mobile, email=email)
        form = TransactionForm(request.POST)
        if form.is_valid():
            # create new transaction and save it
            new_transaction = Transaction()
            new_transaction.description = description
            new_transaction.amount = amount
            new_transaction.mobile = mobile
            new_transaction.authority = zarin_pal.authority
            new_transaction.email = email
            new_transaction.patient = PatientUser.objects.get(user=request.user)
            new_transaction.save()

            # redirect user to zarinpal payment gate to paid
            return redirect(redirect_url)

        # this showing erro not safe!
        return HttpResponse(form.errors.as_json())

    # if got error from zarinpal
    except ZarinpalError as e:
        return HttpResponse(e)


def verify(request):
    if request.GET.get('Status') == 'OK':
        authority = int(request.GET['Authority'])
        try:
            # try to found transaction
            try:
                transaction = Transaction.objects.get(authority=authority)

            # if we couldn't find the transaction
            except ObjectDoesNotExist:
                return HttpResponse('we can\'t find this transaction')

            code, message, ref_id = zarin_pal.payment_verification(transaction.amount, authority)

            # everything is okey
            if code == 100:
                transaction.reference_id = ref_id
                transaction.patient.balance = transaction.patient.balance + transaction.amount
                transaction.patient.save()
                transaction.save()
                content = {
                    'type': 'Success',
                    'ref_id': ref_id
                }
                return render(request, 'website/transaction_status.html', context=content)
            # operation was successful but PaymentVerification operation on this transaction have already been done
            elif code == 101:
                content = {
                    'type': 'Warning'
                }
                return render(request, 'website/transaction_status.html', context=content)

        # if got an error from zarinpal
        except ZarinpalError as e:
            return HttpResponse(e)

    return render(request, 'website/transaction_status.html')


def transactions(request):
    all_transaction = Transaction.objects.filter(patient=PatientUser.objects.get(user=request.user))
    content = {
        'transactions': all_transaction
    }
    return render(request, 'website/transactions.html', context=content)


class TicketsView(ListView):
    model = Ticket
    paginate_by = 10  # if pagination is desired

    def get_queryset(self):
        return Ticket.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_form'] = CreateTicketForm()
        return context


def create_ticket(request):
    if request.method == "POST":
        form = CreateTicketForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.user = request.user
            instance.save()
    return redirect(reverse_lazy('website:tickets'))


@login_required(login_url='signup/patient')
def patient_visits(request):
    visits = Visit.objects.filter(patient=PatientUser.objects.get(user=request.user), state='N')
    content = {
        'list': visits
    }
    return render(request, 'website/patient_visits.html', context=content)


@login_required(login_url='signup/doctor')
def doctor_visits(request):
    visits = Visit.objects.filter(doctor=DoctorUser.objects.get(user=request.user), state='N')
    content = {
        'list': visits
    }
    return render(request, 'website/doctor_visits.html', context=content)


@login_required(login_url='signup/patient')
def patient_cancel_visit(request, pk):
    visit = Visit.objects.get(pk=pk)
    if abs(visit.start_time.timestamp() - (datetime.datetime.now().timestamp() + 4.5 * 3600)) <= 24 * 60 * 60:
        message = "Too Close Too Visit Time. You can't cancel now"
        context = {
            'message': message,
        }
        return render(request, 'website/patient_visits.html', context=context)
    else:
        decrease_percentage = 0.3
        patient = visit.patient
        patient.balance += visit.price * (1 - decrease_percentage)
        patient.save()
        visit.state = 'P'
        visit.save()
        message = 'Visit canceled successfully'
        context = {
            'message': message,
        }
        return render(request, 'website/patient_visits.html', context=context)


@login_required(login_url='signup/patient')
def doctor_cancel_visit(request, pk):
    visit = Visit.objects.get(pk=pk)
    if abs(visit.start_time.timestamp() - (datetime.datetime.now().timestamp() + 4.5 * 3600)) <= 24 * 60 * 60:
        message = "Too Close Too Visit Time. You can't cancel now"
        context = {
            'message': message,
        }
        return render(request, 'website/doctor_visits.html', context=context)
    else:
        patient = visit.patient
        patient.balance += visit.price
        patient.save()
        visit.state = 'D'
        visit.save()
        message = 'Visit canceled successfully'
        context = {
            'message': message,
        }
        return render(request, 'website/doctor_visits.html', context=context)
