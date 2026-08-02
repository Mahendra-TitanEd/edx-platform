"""
Views for Platform Admin application
"""

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from common.djangoapps.edxmako.shortcuts import render_to_response
from college.models import CollegeStudent
import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def platform_admin_dashboard(request):
    """
    Main platform admin dashboard view

    Renders the platform administration overview with billing,
    subscriptions, and plan information.
    """
    # Get college name if available
    college_name = ""
    try:
        college_student = CollegeStudent.objects.get(user=request.user)
        college = college_student.college
        college_name = college.name if hasattr(college, 'name') else ""
    except Exception as e:
        logger.warning(f"Could not get college info for user {request.user.id}: {e}")
        # Continue anyway - college_name will be empty string

    context = {
        'college_name': college_name,
    }

    return render_to_response(
        'platform_admin/platform_admin.html',
        context
    )


@login_required
@require_http_methods(["GET"])
def billing_overview(request):
    """
    Billing and subscription management view
    """
    # Get college name if available
    college_name = ""
    try:
        college_student = CollegeStudent.objects.get(user=request.user)
        college = college_student.college
        college_name = college.name if hasattr(college, 'name') else ""
    except Exception as e:
        logger.warning(f"Could not get college info for user {request.user.id}: {e}")

    context = {
        'college_name': college_name,
    }

    return render_to_response(
        'platform_admin/billing.html',
        context
    )


@login_required
@require_http_methods(["GET"])
def pa_seat_management(request):
    """
    Seat Management view
    """
    context = {}
    return render_to_response(
        'platform_admin/pa_seats_management.html',
        context
    )


@login_required
@require_http_methods(["GET"])
def pa_programmes(request):
    """
    Programmes management view
    """
    context = {}
    return render_to_response(
        'platform_admin/pa_programmes.html',
        context
    )


@login_required
@require_http_methods(["GET"])
def pa_branding(request):
    """
    Branding configuration view
    """
    context = {}
    return render_to_response(
        'platform_admin/pa_branding.html',
        context
    )


@login_required
@require_http_methods(["GET"])
def pa_users_accounts(request):
    """
    Users & Accounts management view - Overview
    """
    context = {
        'current_page': 'overview',
    }
    return render_to_response(
        'platform_admin/pa_users_accounts.html',
        context
    )


@login_required
@require_http_methods(["GET"])
def pa_student_list(request):
    """
    Student List view
    """
    context = {
        'current_page': 'student_list',
    }
    return render_to_response(
        'platform_admin/pa_student_list.html',
        context
    )


@login_required
@require_http_methods(["GET"])
def pa_import_students(request):
    """
    Import Students view
    """
    context = {
        'current_page': 'import_students',
    }
    return render_to_response(
        'platform_admin/pa_import_students.html',
        context
    )


@login_required
@require_http_methods(["GET"])
def pa_access_requests(request):
    """
    Access Requests view
    """
    context = {
        'current_page': 'access_requests',
    }
    return render_to_response(
        'platform_admin/pa_access_requests.html',
        context
    )


@login_required
@require_http_methods(["GET"])
def pa_staff_overview(request):
    """
    Staff Overview view
    """
    context = {
        'current_page': 'staff_overview',
    }
    return render_to_response(
        'platform_admin/pa_staff_overview.html',
        context
    )


@login_required
@require_http_methods(["GET"])
def pa_faculty_admins(request):
    """
    Faculty Admins view
    """
    context = {
        'current_page': 'faculty_admins',
    }
    return render_to_response(
        'platform_admin/pa_faculty_admins.html',
        context
    )


@login_required
@require_http_methods(["GET"])
def pa_institution_admins(request):
    """
    Institution Admins view
    """
    context = {
        'current_page': 'institution_admins',
    }
    return render_to_response(
        'platform_admin/pa_institution_admins.html',
        context
    )


@login_required
@require_http_methods(["GET"])
def pa_import_faculty(request):
    """
    Import Faculty view
    """
    context = {
        'current_page': 'import_faculty',
    }
    return render_to_response(
        'platform_admin/pa_import_faculty.html',
        context
    )


@login_required
@require_http_methods(["GET"])
def pa_sync_log(request):
    """
    Sync Log view — SSO / enrolment access events
    """
    context = {
        'current_page': 'sync_log',
    }
    return render_to_response(
        'platform_admin/pa_sync_log.html',
        context
    )
