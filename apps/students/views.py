from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from datetime import date, datetime, timedelta
from .models import StudentExtra
from apps.members.models import LibraryMembership
from apps.core.models import Library, AdminProfile
from .filters import StudentFilter
from django.contrib import messages
import json
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
import logging
from django.contrib.auth import update_session_auth_hash

logger = logging.getLogger(__name__)


# -------------------- STUDENT MANAGEMENT VIEWS --------------------


from apps.core.views import library_required


@library_required
def addstudent_view(request):
    """Add a new student to the current library."""
    library = request.library
    from .forms import StudentExtraForm

    form = StudentExtraForm(library)
    if request.method == "POST":
        form = StudentExtraForm(library, request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.library = library
            student.save()
            return redirect("studentadded")
    return render(
        request, "student/addstudent.html", {"form": form, "library": library}
    )


@login_required
def studentadded_view(request):
    return render(request, "student/studentadded.html")


@library_required
def viewstudent_view(request):
    """View all students in the current library."""
    library = request.library
    # Get students from current library only, sorted by name A-Z
    students = StudentExtra.objects.filter(library=library).order_by("name")

    # Search functionality
    query = request.GET.get("q", "").strip()
    if query and query != "None":  # Handle the "None" string case
        students = students.filter(
            Q(name__icontains=query) | Q(enrollment__icontains=query)
        )

    # Initialize filter - use StudentFilter directly
    student_filter = StudentFilter(request.GET, queryset=students)
    students = student_filter.qs

    # Pagination (10 per page)
    paginator = Paginator(students, 10)
    page = request.GET.get("page")

    try:
        students = paginator.page(page)
    except PageNotAnInteger:
        students = paginator.page(1)
    except EmptyPage:
        students = paginator.page(paginator.num_pages)

    return render(
        request,
        "student/viewstudent.html",
        {
            "students": students,
            "filter": student_filter,
            "query": query if query != "None" else "",
            "gender_choices": StudentExtra.GENDER_CHOICES,
            "library": library,
        },
    )


@library_required
def delete_students_view(request):
    """Delete students from current library."""
    library = request.library
    if request.method == "POST":
        selected_students = request.POST.getlist("selected_students")
        if selected_students:
            # Only delete students from current library
            deleted_count, _ = StudentExtra.objects.filter(
                id__in=selected_students, library=library
            ).delete()
            messages.success(
                request, f"{deleted_count} Student(s) deleted successfully!"
            )
        else:
            messages.warning(request, "No student selected for deletion.")
        return redirect("viewstudent")
    return redirect("viewstudent")


@library_required
def update_students_view(request):
    """Update students in current library."""
    library = request.library
    if request.method == "POST":
        students_data = json.loads(request.POST.get("students_data", "[]"))
        for student_data in students_data:
            try:
                # Only update students from current library
                student = StudentExtra.objects.get(
                    id=student_data["id"], library=library
                )
                student.name = student_data["name"]
                student.enrollment = student_data["enrollment"]
                student.address = student_data["address"]
                student.phone = student_data["phone"]
                student.gender = student_data["gender"]
                student.save()
            except StudentExtra.DoesNotExist:
                continue

        messages.success(request, "Student(s) updated successfully!")
        return redirect("viewstudent")
    return redirect("viewstudent")
