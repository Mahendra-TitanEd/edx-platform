"""
URL configuration for Platform Admin application
"""

from django.urls import path
from django.http import HttpResponse
from . import views
from . import api_views

app_name = 'platform_admin'

# Simple test view for debugging
def test_view(request):
    return HttpResponse("""
        <h1>Platform Admin - Routing Test</h1>
        <p>✅ If you see this, the URL routing is working correctly!</p>
        <p>User: {}</p>
        <hr>
        <h3>Available URLs:</h3>
        <ul>
            <li><a href="/platform-admin/">Dashboard</a></li>
            <li><a href="/platform-admin/billing/">Billing</a></li>
        </ul>
    """.format(request.user.username if request.user.is_authenticated else 'Not logged in'))

urlpatterns = [
    path('test/', test_view, name='test'),  # Test URL for debugging
    path('', views.platform_admin_dashboard, name='dashboard'),
    path('users-accounts/', views.pa_users_accounts, name='users_accounts'),
    path('users-accounts/student-list/', views.pa_student_list, name='student_list'),
    path('users-accounts/import-students/', views.pa_import_students, name='import_students'),
    path('users-accounts/access-requests/', views.pa_access_requests, name='access_requests'),
    path('users-accounts/staff-overview/', views.pa_staff_overview, name='staff_overview'),
    path('users-accounts/faculty-admins/', views.pa_faculty_admins, name='faculty_admins'),
    path('users-accounts/institution-admins/', views.pa_institution_admins, name='institution_admins'),
    path('users-accounts/import-faculty/', views.pa_import_faculty, name='import_faculty'),
    path('seat-management/', views.pa_seat_management, name='seat_management'),
    path('programmes/', views.pa_programmes, name='programmes'),
    path('branding/', views.pa_branding, name='branding'),
    path('billing/', views.billing_overview, name='billing'),
    path('sync-log/', views.pa_sync_log, name='sync_log'),

    # Programme API endpoints
    path('api/programmes/', api_views.list_programmes, name='api_list_programmes'),
    path('api/programmes/create/', api_views.create_programme, name='api_create_programme'),
    path('api/programmes/<int:programme_id>/', api_views.get_programme, name='api_get_programme'),
    path('api/programmes/<int:programme_id>/update/', api_views.update_programme, name='api_update_programme'),
    path('api/programmes/<int:programme_id>/delete/', api_views.delete_programme, name='api_delete_programme'),
    path('api/programmes/<int:programme_id>/sections/add/', api_views.add_section, name='api_add_section'),
    path('api/programmes/<int:programme_id>/sections/rename/', api_views.rename_section, name='api_rename_section'),
    path('api/programmes/<int:programme_id>/sections/delete/', api_views.delete_section, name='api_delete_section'),

    # Group API endpoints
    path('api/groups/', api_views.list_groups, name='api_list_groups'),
    path('api/groups/create/', api_views.create_group, name='api_create_group'),
    path('api/groups/<int:group_id>/update/', api_views.update_group, name='api_update_group'),
    path('api/groups/<int:group_id>/delete/', api_views.delete_group, name='api_delete_group'),

    # User API endpoints
    path('api/users/', api_views.list_users, name='api_list_users'),

    # Student API endpoints
    path('api/students/', api_views.list_students, name='api_list_students'),
    path('api/students/create/', api_views.create_student, name='api_create_student'),
    path('api/students/<int:student_id>/', api_views.get_student, name='api_get_student'),
    path('api/students/<int:student_id>/update/', api_views.update_student, name='api_update_student'),
    path('api/students/<int:student_id>/delete/', api_views.delete_student, name='api_delete_student'),
    path('api/students/<int:student_id>/suspend/', api_views.suspend_student, name='api_suspend_student'),
    path('api/students/<int:student_id>/reactivate/', api_views.reactivate_student, name='api_reactivate_student'),
    path('api/students/<int:student_id>/archive/', api_views.archive_student, name='api_archive_student'),

    # Bulk student actions
    path('api/students/bulk/move-section/', api_views.bulk_move_section, name='api_bulk_move_section'),
    path('api/students/bulk/update-status/', api_views.bulk_update_status, name='api_bulk_update_status'),
    path('api/students/bulk/export-csv/', api_views.bulk_export_csv, name='api_bulk_export_csv'),
    path('api/students/bulk/delete/', api_views.bulk_delete_students, name='api_bulk_delete_students'),
    path('api/students/bulk/advance-year/', api_views.bulk_advance_year, name='api_bulk_advance_year'),

    # Overview stats
    path('api/students/overview-stats/', api_views.get_student_overview_stats, name='api_student_overview_stats'),

    # Student import endpoints
    path('api/students/import/template/', api_views.download_student_template, name='api_download_student_template'),
    path('api/students/import/csv/', api_views.import_students_csv, name='api_import_students_csv'),

    # Faculty Admin API endpoints
    path('api/faculty-admins/', api_views.list_faculty_admins, name='api_list_faculty_admins'),
    path('api/faculty-admins/create/', api_views.create_faculty_admin, name='api_create_faculty_admin'),
    path('api/faculty-admins/<int:faculty_id>/update/', api_views.update_faculty_admin, name='api_update_faculty_admin'),
    path('api/faculty-admins/<int:faculty_id>/promote/', api_views.promote_faculty_to_admin, name='api_promote_faculty_to_admin'),
    path('api/faculty-admins/programmes/', api_views.get_programmes_for_faculty, name='api_get_programmes_for_faculty'),

    # Faculty import endpoints
    path('api/faculty/import/template/', api_views.download_faculty_template, name='api_download_faculty_template'),
    path('api/faculty/import/csv/', api_views.import_faculty_csv, name='api_import_faculty_csv'),

    # Institution Admin API endpoints
    path('api/institution-admins/', api_views.list_institution_admins, name='api_list_institution_admins'),
    path('api/institution-admins/create/', api_views.create_institution_admin, name='api_create_institution_admin'),
    path('api/institution-admins/<int:admin_id>/update/', api_views.update_institution_admin, name='api_update_institution_admin'),

    # Seat Management API endpoints
    path('api/seat-management/', api_views.get_seat_management_data, name='api_get_seat_management_data'),
    path('api/seat-management/update/', api_views.update_programme_seat_allocations, name='api_update_programme_seat_allocations'),

    # Platform Admin Overview/Dashboard API endpoint
    path('api/overview/', api_views.get_platform_overview, name='api_get_platform_overview'),
    path('api/staff-overview/', api_views.get_staff_overview, name='api_get_staff_overview'),

    # Sync Log API
    path('api/sync-log/', api_views.list_sync_log, name='api_list_sync_log'),
    path('api/sync-log/export/', api_views.export_sync_log, name='api_export_sync_log'),
]
