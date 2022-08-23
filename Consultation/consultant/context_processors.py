from website.models import PatientUser, DoctorUser


def user_type_processor(request):
    is_patient = False
    is_doctor = False
    validated = False
    if request.user and request.user.is_authenticated:
        is_patient = PatientUser.objects.filter(user=request.user).exists()
    if request.user and request.user.is_authenticated:
        is_doctor = DoctorUser.objects.filter(user=request.user).exists()
    if request.user and request.user.is_authenticated and is_doctor:
        validated = DoctorUser.objects.get(user=request.user).state == 'A'
    return {
        'is_patient': is_patient,
        'is_doctor': is_doctor,
        'validated': validated,
    }
