"""
API Views for Platform Admin - Programmes Management
"""

import json
import logging
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Count, Prefetch, Q

from college.models import CollegeStudent
from lms.djangoapps.university_programme.models import (
    UniversityProgrammes,
    UniversityProgrammesYear,
    UniversityProgrammesYearSection,
    UniversityProgrammesEnrolment,
)

logger = logging.getLogger(__name__)


def get_user_college(user):
    """Get the college/university associated with the authenticated user"""
    try:
        college_student = CollegeStudent.objects.select_related('college').get(user=user)
        return college_student.college
    except CollegeStudent.DoesNotExist:
        return None


@login_required
@require_http_methods(["GET"])
def list_programmes(request):
    """
    List all programmes for the logged-in user's university
    Returns JSON with programme data including years and sections
    """
    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        # Fetch programmes with related data using prefetch
        programmes = UniversityProgrammes.objects.filter(
            university=college
        ).prefetch_related(
            Prefetch(
                'programme_years',
                queryset=UniversityProgrammesYear.objects.prefetch_related(
                    Prefetch(
                        'year_sections',
                        queryset=UniversityProgrammesYearSection.objects.all()
                    )
                )
            )
        ).annotate(
            student_count=Count('universityprogrammesenrolment', distinct=True)
        ).order_by('short_name')

        programmes_data = []
        for prog in programmes:
            # Build subgroups structure with years and sections
            subgroups = []
            for year in prog.programme_years.all():
                subgroups.append({
                    'name': year.number_of_year,
                    'sections': [section.name for section in year.year_sections.all()]
                })

            programmes_data.append({
                'id': prog.id,
                'short_name': prog.short_name,
                'name': prog.name,
                'description': prog.description or '',
                'duration': prog.duration,
                'years': prog.get_duration_years(),
                'color': prog.color or '#1f4d3a',
                'status': prog.status,
                'enable_mystudio': prog.enable_mystudio,
                'enable_careers_app': prog.enable_careers_app,
                'allocated_seats': prog.allocated_seats,
                'student_count': prog.student_count,
                'subgroups': subgroups
            })

        return JsonResponse({
            'success': True,
            'programmes': programmes_data
        })

    except Exception as e:
        logger.error(f"Error listing programmes: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_programme(request, programme_id):
    """Get details of a specific programme"""
    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        prog = UniversityProgrammes.objects.prefetch_related(
            Prefetch(
                'programme_years',
                queryset=UniversityProgrammesYear.objects.prefetch_related(
                    Prefetch(
                        'year_sections',
                        queryset=UniversityProgrammesYearSection.objects.all()
                    )
                )
            )
        ).get(id=programme_id, university=college)

        # Build subgroups structure
        subgroups = []
        for year in prog.programme_years.all():
            subgroups.append({
                'name': year.number_of_year,
                'sections': [section.name for section in year.year_sections.all()]
            })

        return JsonResponse({
            'success': True,
            'programme': {
                'id': prog.id,
                'short_name': prog.short_name,
                'name': prog.name,
                'description': prog.description or '',
                'duration': prog.duration,
                'years': prog.get_duration_years(),
                'color': prog.color or '#1f4d3a',
                'status': prog.status,
                'enable_mystudio': prog.enable_mystudio,
                'enable_careers_app': prog.enable_careers_app,
                'allocated_seats': prog.allocated_seats,
                'subgroups': subgroups
            }
        })

    except UniversityProgrammes.DoesNotExist:
        return JsonResponse({'error': 'Programme not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting programme: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_programme(request):
    """
    Create a new programme with years and sections
    Automatically associates with the logged-in user's university
    """
    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        data = json.loads(request.body)

        # Validate required fields
        if not data.get('short_name') or not data.get('name'):
            return JsonResponse({'error': 'Short name and full name are required'}, status=400)

        # Check for duplicate short_name in the same university
        if UniversityProgrammes.objects.filter(
            university=college,
            short_name=data['short_name']
        ).exists():
            return JsonResponse({
                'error': f'Programme with short name "{data["short_name"]}" already exists'
            }, status=400)

        # Validate allocated_seats
        allocated_seats = data.get('allocated_seats', 0)
        if allocated_seats < 0:
            return JsonResponse({'error': 'Allocated seats cannot be negative'}, status=400)

        # Validate university seat capacity
        university_max_seats = college.max_students
        if university_max_seats > 0:  # Only validate if max_students is set
            # Calculate total allocated seats for existing active programmes
            from django.db.models import Sum
            existing_allocated = UniversityProgrammes.objects.filter(
                university=college,
                status='active'
            ).aggregate(total=Sum('allocated_seats'))['total'] or 0

            # Check if adding new programme seats exceeds university capacity
            total_after_creation = existing_allocated + allocated_seats
            if total_after_creation > university_max_seats:
                return JsonResponse({
                    'error': f'Total programme seats ({total_after_creation}) would exceed university capacity ({university_max_seats}). Currently allocated: {existing_allocated} seats.'
                }, status=400)

        with transaction.atomic():
            # Create programme
            programme = UniversityProgrammes.objects.create(
                university=college,
                short_name=data['short_name'],
                name=data['name'],
                description=data.get('description', ''),
                duration=data.get('duration', '5_year'),
                status=data.get('status', 'active'),
                color=data.get('color', '#1f4d3a'),
                enable_mystudio=data.get('enable_mystudio', True),
                enable_careers_app=data.get('enable_careers_app', True),
                allocated_seats=allocated_seats
            )

            # Create years and sections from subgroups
            subgroups = data.get('subgroups', [])
            for subgroup in subgroups:
                year_name = subgroup.get('name', '')
                if not year_name:
                    continue

                year = UniversityProgrammesYear.objects.create(
                    programme=programme,
                    number_of_year=year_name
                )

                # Create sections for this year
                sections = subgroup.get('sections', [])
                for section_name in sections:
                    if section_name and section_name.strip():
                        UniversityProgrammesYearSection.objects.create(
                            programme_year=year,
                            name=section_name.strip()
                        )

        return JsonResponse({
            'success': True,
            'message': 'Programme created successfully',
            'programme_id': programme.id
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error creating programme: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_programme(request, programme_id):
    """
    Update an existing programme
    Replaces years and sections with new data
    """
    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        data = json.loads(request.body)

        # Validate required fields
        if not data.get('short_name') or not data.get('name'):
            return JsonResponse({'error': 'Short name and full name are required'}, status=400)

        with transaction.atomic():
            # Get programme
            programme = UniversityProgrammes.objects.select_for_update().get(
                id=programme_id,
                university=college
            )

            # Check for duplicate short_name (excluding current programme)
            if UniversityProgrammes.objects.filter(
                university=college,
                short_name=data['short_name']
            ).exclude(id=programme_id).exists():
                return JsonResponse({
                    'error': f'Programme with short name "{data["short_name"]}" already exists'
                }, status=400)

            # Validate seat allocation if being updated
            new_allocated_seats = data.get('allocated_seats', programme.allocated_seats)
            if new_allocated_seats != programme.allocated_seats:
                university_max_seats = college.max_students
                if university_max_seats > 0:  # Only validate if max_students is set
                    # Calculate total allocated seats for other active programmes (excluding current one)
                    from django.db.models import Sum
                    other_allocated = UniversityProgrammes.objects.filter(
                        university=college,
                        status='active'
                    ).exclude(id=programme_id).aggregate(total=Sum('allocated_seats'))['total'] or 0

                    # Check if updating seats exceeds university capacity
                    total_after_update = other_allocated + new_allocated_seats
                    if total_after_update > university_max_seats:
                        return JsonResponse({
                            'error': f'Total programme seats ({total_after_update}) would exceed university capacity ({university_max_seats}). Currently allocated to other programmes: {other_allocated} seats.'
                        }, status=400)

            # Update programme fields
            programme.short_name = data['short_name']
            programme.name = data['name']
            programme.description = data.get('description', '')
            programme.duration = data.get('duration', programme.duration)
            programme.status = data.get('status', programme.status)
            programme.color = data.get('color', programme.color)
            programme.enable_mystudio = data.get('enable_mystudio', programme.enable_mystudio)
            programme.enable_careers_app = data.get('enable_careers_app', programme.enable_careers_app)
            programme.allocated_seats = new_allocated_seats
            programme.save()

            # Delete existing years and sections
            programme.programme_years.all().delete()

            # Create new years and sections from subgroups
            subgroups = data.get('subgroups', [])
            for subgroup in subgroups:
                year_name = subgroup.get('name', '')
                if not year_name:
                    continue

                year = UniversityProgrammesYear.objects.create(
                    programme=programme,
                    number_of_year=year_name
                )

                # Create sections for this year
                sections = subgroup.get('sections', [])
                for section_name in sections:
                    if section_name and section_name.strip():
                        UniversityProgrammesYearSection.objects.create(
                            programme_year=year,
                            name=section_name.strip()
                        )

        return JsonResponse({
            'success': True,
            'message': 'Programme updated successfully'
        })

    except UniversityProgrammes.DoesNotExist:
        return JsonResponse({'error': 'Programme not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error updating programme: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def delete_programme(request, programme_id):
    """Delete a programme and all its related data"""
    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        with transaction.atomic():
            programme = UniversityProgrammes.objects.get(
                id=programme_id,
                university=college
            )
            programme_name = programme.short_name
            programme.delete()

        return JsonResponse({
            'success': True,
            'message': f'Programme "{programme_name}" deleted successfully'
        })

    except UniversityProgrammes.DoesNotExist:
        return JsonResponse({'error': 'Programme not found'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting programme: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def add_section(request, programme_id):
    """Add a new section to a specific year of a programme"""
    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        data = json.loads(request.body)
        year_name = data.get('year_name')
        section_name = data.get('section_name', '').strip()

        if not year_name or not section_name:
            return JsonResponse({'error': 'Year name and section name are required'}, status=400)

        # Get programme and verify ownership
        programme = UniversityProgrammes.objects.get(
            id=programme_id,
            university=college
        )

        # Get the year
        year = UniversityProgrammesYear.objects.get(
            programme=programme,
            number_of_year=year_name
        )

        # Check if section already exists
        if UniversityProgrammesYearSection.objects.filter(
            programme_year=year,
            name=section_name
        ).exists():
            return JsonResponse({
                'error': f'Section "{section_name}" already exists in {year_name}'
            }, status=400)

        # Create section
        UniversityProgrammesYearSection.objects.create(
            programme_year=year,
            name=section_name
        )

        return JsonResponse({
            'success': True,
            'message': f'Section "{section_name}" added to {year_name}'
        })

    except UniversityProgrammes.DoesNotExist:
        return JsonResponse({'error': 'Programme not found'}, status=404)
    except UniversityProgrammesYear.DoesNotExist:
        return JsonResponse({'error': 'Year not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error adding section: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def rename_section(request, programme_id):
    """Rename a section in a specific year of a programme"""
    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        data = json.loads(request.body)
        year_name = data.get('year_name')
        old_name = data.get('old_name', '').strip()
        new_name = data.get('new_name', '').strip()

        if not year_name or not old_name or not new_name:
            return JsonResponse({'error': 'Year name, old name, and new name are required'}, status=400)

        # Get programme and verify ownership
        programme = UniversityProgrammes.objects.get(
            id=programme_id,
            university=college
        )

        # Get the year
        year = UniversityProgrammesYear.objects.get(
            programme=programme,
            number_of_year=year_name
        )

        # Get the section to rename
        section = UniversityProgrammesYearSection.objects.get(
            programme_year=year,
            name=old_name
        )

        # Check if new name already exists
        if UniversityProgrammesYearSection.objects.filter(
            programme_year=year,
            name=new_name
        ).exclude(id=section.id).exists():
            return JsonResponse({
                'error': f'Section "{new_name}" already exists in {year_name}'
            }, status=400)

        # Rename section
        section.name = new_name
        section.save()

        return JsonResponse({
            'success': True,
            'message': f'Section renamed from "{old_name}" to "{new_name}"'
        })

    except UniversityProgrammes.DoesNotExist:
        return JsonResponse({'error': 'Programme not found'}, status=404)
    except UniversityProgrammesYear.DoesNotExist:
        return JsonResponse({'error': 'Year not found'}, status=404)
    except UniversityProgrammesYearSection.DoesNotExist:
        return JsonResponse({'error': 'Section not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error renaming section: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def delete_section(request, programme_id):
    """Delete a section from a specific year of a programme"""
    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        data = json.loads(request.body)
        year_name = data.get('year_name')
        section_name = data.get('section_name', '').strip()

        if not year_name or not section_name:
            return JsonResponse({'error': 'Year name and section name are required'}, status=400)

        # Get programme and verify ownership
        programme = UniversityProgrammes.objects.get(
            id=programme_id,
            university=college
        )

        # Get the year
        year = UniversityProgrammesYear.objects.get(
            programme=programme,
            number_of_year=year_name
        )

        # Get and delete the section
        section = UniversityProgrammesYearSection.objects.get(
            programme_year=year,
            name=section_name
        )
        section.delete()

        return JsonResponse({
            'success': True,
            'message': 'Section deleted successfully'
        })

    except UniversityProgrammes.DoesNotExist:
        return JsonResponse({'error': 'Programme not found'}, status=404)
    except UniversityProgrammesYear.DoesNotExist:
        return JsonResponse({'error': 'Year not found'}, status=404)
    except UniversityProgrammesYearSection.DoesNotExist:
        return JsonResponse({'error': 'Section not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error deleting section: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# GROUP API ENDPOINTS
# ============================================================================

@login_required
@require_http_methods(["GET"])
def list_groups(request):
    """List all groups for the logged-in user's university"""
    from course_playlist.models import StudentsGroup

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        groups = StudentsGroup.objects.filter(
            college=college
        ).select_related('programme', 'admin').annotate(
            student_count=Count('students', distinct=True)
        ).order_by('name')

        groups_data = []
        for group in groups:
            # Handle groups with or without programme association
            programme_id = group.programme.id if group.programme else None
            programme_name = group.programme.short_name if group.programme else ''
            admin_name = group.admin.get_full_name() or group.admin.username if group.admin else ''

            groups_data.append({
                'id': group.id,
                'name': group.name,
                'programme_id': programme_id,
                'programme_name': programme_name,
                'group_type': group.group_type or '',
                'admin': admin_name,
                'admin_id': group.admin.id if group.admin else None,
                'description': group.description or '',
                'colour': group.colour or '#1f4d3a',
                'student_count': group.student_count
            })

        return JsonResponse({
            'success': True,
            'groups': groups_data
        })

    except Exception as e:
        logger.error(f"Error listing groups: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_group(request):
    """Create a new group"""
    from django.contrib.auth.models import User
    from course_playlist.models import StudentsGroup

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        data = json.loads(request.body)

        # Validate required fields
        if not data.get('name'):
            return JsonResponse({'error': 'Group name is required'}, status=400)

        # Programme is optional now
        programme = None
        if data.get('programme_id'):
            try:
                programme = UniversityProgrammes.objects.get(
                    id=data['programme_id'],
                    university=college
                )
            except UniversityProgrammes.DoesNotExist:
                return JsonResponse({'error': 'Invalid programme'}, status=400)

        # Check for duplicate group name in the same college
        if StudentsGroup.objects.filter(
            college=college,
            name=data['name']
        ).exists():
            return JsonResponse({
                'error': f'Group with name "{data["name"]}" already exists'
            }, status=400)

        # Map frontend group type to backend choices
        group_type_map = {
            'career-track': 'career_track',
            'teaching': 'teaching_group'
        }
        group_type = group_type_map.get(data.get('group_type', 'career-track'), 'career_track')

        # Get admin user if admin_id provided
        admin_user = None
        if data.get('admin_id'):
            try:
                admin_user = User.objects.get(id=data['admin_id'])
            except User.DoesNotExist:
                return JsonResponse({'error': 'Invalid admin user'}, status=400)

        # Create group
        group = StudentsGroup.objects.create(
            college=college,
            programme=programme,
            name=data['name'],
            group_type=group_type,
            admin=admin_user,
            description=data.get('description', ''),
            colour=data.get('colour', '#1f4d3a')
        )

        return JsonResponse({
            'success': True,
            'message': 'Group created successfully',
            'group_id': group.id
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error creating group: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_group(request, group_id):
    """Update an existing group"""
    from django.contrib.auth.models import User
    from course_playlist.models import StudentsGroup

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        data = json.loads(request.body)

        # Validate required fields
        if not data.get('name'):
            return JsonResponse({'error': 'Group name is required'}, status=400)

        with transaction.atomic():
            # Get group
            group = StudentsGroup.objects.select_for_update().get(
                id=group_id,
                college=college
            )

            # Programme is optional
            programme = None
            if data.get('programme_id'):
                try:
                    programme = UniversityProgrammes.objects.get(
                        id=data['programme_id'],
                        university=college
                    )
                except UniversityProgrammes.DoesNotExist:
                    return JsonResponse({'error': 'Invalid programme'}, status=400)

            # Check for duplicate group name (excluding current group)
            if StudentsGroup.objects.filter(
                college=college,
                name=data['name']
            ).exclude(id=group_id).exists():
                return JsonResponse({
                    'error': f'Group with name "{data["name"]}" already exists'
                }, status=400)

            # Map frontend group type to backend choices
            group_type_map = {
                'career-track': 'career_track',
                'teaching': 'teaching_group'
            }
            group_type = group_type_map.get(data.get('group_type', group.group_type), group.group_type)

            # Get admin user if admin_id provided
            admin_user = group.admin  # Keep existing if not provided
            if 'admin_id' in data:
                if data['admin_id']:
                    try:
                        admin_user = User.objects.get(id=data['admin_id'])
                    except User.DoesNotExist:
                        return JsonResponse({'error': 'Invalid admin user'}, status=400)
                else:
                    admin_user = None

            # Update group fields
            group.name = data['name']
            group.programme = programme
            group.group_type = group_type
            group.admin = admin_user
            group.description = data.get('description', group.description)
            group.colour = data.get('colour', group.colour)
            group.save()

        return JsonResponse({
            'success': True,
            'message': 'Group updated successfully'
        })

    except StudentsGroup.DoesNotExist:
        return JsonResponse({'error': 'Group not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error updating group: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def delete_group(request, group_id):
    """Delete a group"""
    from course_playlist.models import StudentsGroup

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        with transaction.atomic():
            group = StudentsGroup.objects.get(
                id=group_id,
                college=college
            )
            group_name = group.name
            group.delete()

        return JsonResponse({
            'success': True,
            'message': f'Group "{group_name}" deleted successfully'
        })

    except StudentsGroup.DoesNotExist:
        return JsonResponse({'error': 'Group not found'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting group: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def list_users(request):
    """List all users from the logged-in user's university for dropdown"""
    from django.contrib.auth.models import User

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        # Get all users associated with this college
        college_students = CollegeStudent.objects.filter(
            college=college
        ).select_related('user').order_by('user__first_name', 'user__last_name')

        users_data = []
        for cs in college_students:
            user = cs.user
            full_name = user.get_full_name() or user.username
            users_data.append({
                'id': user.id,
                'username': user.username,
                'full_name': full_name,
                'email': user.email,
                'display_name': f"{full_name} ({user.username})"
            })

        return JsonResponse({
            'success': True,
            'users': users_data
        })

    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# STUDENT MANAGEMENT API ENDPOINTS
# ============================================================================

@login_required
@require_http_methods(["GET"])
def list_students(request):
    """List all students for the logged-in user's university"""
    from django.contrib.auth.models import User
    from lms.djangoapps.user_metadata.models import UserMetaData
    from common.djangoapps.student.models import UserProfile

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        # Get query parameters for filtering
        search = request.GET.get('search', '').strip()
        status_filter = request.GET.get('status', '').strip()
        programme_filter = request.GET.get('programme_id', '').strip()

        # Base query: all students in this college
        college_students = CollegeStudent.objects.filter(
            college=college
        ).select_related(
            'user',
            'user__profile',
            'user__metadata'
        ).prefetch_related(
            Prefetch(
                'user__programme_enrolments',
                queryset=UniversityProgrammesEnrolment.objects.select_related(
                    'programme',
                    'programme_year',
                    'programme_section'
                ).filter(is_active=True)
            )
        )

        # Apply filters
        if search:
            college_students = college_students.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search)
            )

        if status_filter:
            college_students = college_students.filter(user__metadata__status=status_filter)

        if programme_filter:
            college_students = college_students.filter(
                user__programme_enrolments__programme_id=programme_filter,
                user__programme_enrolments__is_active=True
            )

        # Build response data
        students_data = []
        for cs in college_students:
            user = cs.user

            # Get active enrolment
            enrolment = user.programme_enrolments.first() if user.programme_enrolments.exists() else None

            # Get metadata status
            status = user.metadata.status if hasattr(user, 'metadata') else 'inactive'

            students_data.append({
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'name': user.get_full_name() or user.username,
                'email': user.email,
                'programme_name': enrolment.programme.name if enrolment and enrolment.programme else None,
                'programme_id': enrolment.programme.id if enrolment and enrolment.programme else None,
                'year_name': enrolment.programme_year.number_of_year if enrolment and enrolment.programme_year else None,
                'year_id': enrolment.programme_year.id if enrolment and enrolment.programme_year else None,
                'section_name': enrolment.programme_section.name if enrolment and enrolment.programme_section else None,
                'section_id': enrolment.programme_section.id if enrolment and enrolment.programme_section else None,
                'status': status,
                'studio': user.metadata.studio if hasattr(user, 'metadata') else False,
                'careers_app': user.metadata.careers_app if hasattr(user, 'metadata') else False,
                'created': user.date_joined.strftime('%Y-%m-%d') if user.date_joined else '',
            })

        return JsonResponse({
            'success': True,
            'students': students_data
        })

    except Exception as e:
        logger.error(f"Error listing students: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_student(request):
    """Create a new student with User, Profile, Metadata, and Enrolment"""
    from lms.djangoapps.platform_admin.student_service import StudentService, StudentValidationError

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        data = json.loads(request.body)

        # Extract fields
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        email = data.get('email', '')
        programme_id = data.get('programme_id')
        year_name = data.get('year_name', '')
        section_name = data.get('section_name', '')

        # Use service to create student
        result = StudentService.create_student(
            college=college,
            first_name=first_name,
            last_name=last_name,
            email=email,
            programme_id=programme_id,
            year_name=year_name,
            section_name=section_name
        )

        return JsonResponse({
            'success': True,
            'message': result['message'],
            'student_id': result['user_id']
        })

    except StudentValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error creating student: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_student(request, student_id):
    """Get detailed information about a specific student"""
    from django.contrib.auth.models import User

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        # Verify student belongs to this college
        try:
            college_student = CollegeStudent.objects.select_related(
                'user',
                'user__profile',
                'user__metadata'
            ).prefetch_related(
                Prefetch(
                    'user__programme_enrolments',
                    queryset=UniversityProgrammesEnrolment.objects.select_related(
                        'programme',
                        'programme_year',
                        'programme_section'
                    ).filter(is_active=True)
                )
            ).get(user_id=student_id, college=college)
        except CollegeStudent.DoesNotExist:
            return JsonResponse({'error': 'Student not found or does not belong to your university'}, status=404)

        user = college_student.user
        enrolment = user.programme_enrolments.first() if user.programme_enrolments.exists() else None
        metadata = user.metadata if hasattr(user, 'metadata') else None

        student_data = {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'programme_id': enrolment.programme.id if enrolment else None,
            'programme_name': enrolment.programme.short_name if enrolment else None,
            'year_name': enrolment.programme_year.number_of_year if enrolment else None,
            'section_name': enrolment.programme_section.name if enrolment else None,
            'status': metadata.status if metadata else 'inactive',
        }

        return JsonResponse({
            'success': True,
            'student': student_data
        })

    except Exception as e:
        logger.error(f"Error getting student: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_student(request, student_id):
    """Update student information"""
    from django.contrib.auth.models import User
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    from common.djangoapps.student.models import UserProfile
    from lms.djangoapps.user_metadata.models import UserMetaData

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        data = json.loads(request.body)

        # Validate student belongs to college
        try:
            college_student = CollegeStudent.objects.get(user_id=student_id, college=college)
        except CollegeStudent.DoesNotExist:
            return JsonResponse({'error': 'Student not found or does not belong to your university'}, status=404)

        user = college_student.user

        # Parse fields - only programme enrollment and metadata
        programme_id = data.get('programme_id')
        year_name = data.get('year_name', '').strip()
        section_name = data.get('section_name', '').strip()
        status = data.get('status', '').strip()
        studio = data.get('studio', False)
        careers_app = data.get('careers_app', False)

        # Validate required fields - all must be provided
        if not programme_id:
            return JsonResponse({'error': 'Programme is required'}, status=400)

        if not year_name:
            return JsonResponse({'error': 'Year is required'}, status=400)

        if not section_name:
            return JsonResponse({'error': 'Section is required'}, status=400)

        if not status:
            return JsonResponse({'error': 'Status is required'}, status=400)

        with transaction.atomic():
            # Update UserMetaData (status and app access)
            if hasattr(user, 'metadata'):
                user.metadata.status = status
                user.metadata.studio = studio
                user.metadata.careers_app = careers_app
                user.metadata.save()
            else:
                # Create metadata if it doesn't exist
                UserMetaData.objects.create(
                    user=user,
                    status=status,
                    studio=studio,
                    careers_app=careers_app
                )

            # Update programme enrolment
            # Verify programme belongs to college
            try:
                programme = UniversityProgrammes.objects.get(
                    id=programme_id,
                    university=college
                )
            except UniversityProgrammes.DoesNotExist:
                return JsonResponse({'error': 'Invalid programme'}, status=400)

            # Get programme year
            try:
                programme_year = UniversityProgrammesYear.objects.get(
                    programme=programme,
                    number_of_year=year_name
                )
            except UniversityProgrammesYear.DoesNotExist:
                return JsonResponse({'error': f'Year {year_name} not found'}, status=400)

            # Get programme section
            try:
                programme_section = UniversityProgrammesYearSection.objects.get(
                    programme_year=programme_year,
                    name=section_name
                )
            except UniversityProgrammesYearSection.DoesNotExist:
                return JsonResponse({'error': f'Section {section_name} not found'}, status=400)

            # Update or create enrolment
            # First delete all existing enrolments for this user
            UniversityProgrammesEnrolment.objects.filter(user=user).delete()

            # Create new enrolment with section (section is now required)
            UniversityProgrammesEnrolment.objects.create(
                user=user,
                programme=programme,
                programme_year=programme_year,
                programme_section=programme_section,
                is_active=True
            )

        return JsonResponse({
            'success': True,
            'message': 'Student updated successfully'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error updating student: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def delete_student(request, student_id):
    """Soft delete a student (set status to inactive)"""
    from django.contrib.auth.models import User
    from lms.djangoapps.user_metadata.models import UserMetaData

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        # Verify student belongs to college
        try:
            college_student = CollegeStudent.objects.get(user_id=student_id, college=college)
        except CollegeStudent.DoesNotExist:
            return JsonResponse({'error': 'Student not found or does not belong to your university'}, status=404)

        user = college_student.user

        with transaction.atomic():
            # Soft delete: set status to inactive
            user.is_active = False
            user.save()

            # Update metadata status
            if hasattr(user, 'metadata'):
                user.metadata.status = 'inactive'
                user.metadata.save()
            else:
                UserMetaData.objects.create(
                    user=user,
                    status='inactive'
                )

            # Deactivate enrolments
            UniversityProgrammesEnrolment.objects.filter(
                user=user,
                is_active=True
            ).update(is_active=False)

        return JsonResponse({
            'success': True,
            'message': f'Student {user.get_full_name()} deleted successfully'
        })

    except Exception as e:
        logger.error(f"Error deleting student: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def suspend_student(request, student_id):
    """Suspend a student"""
    from lms.djangoapps.user_metadata.models import UserMetaData

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        # Verify student belongs to college
        try:
            college_student = CollegeStudent.objects.get(user_id=student_id, college=college)
        except CollegeStudent.DoesNotExist:
            return JsonResponse({'error': 'Student not found or does not belong to your university'}, status=404)

        user = college_student.user

        with transaction.atomic():
            if hasattr(user, 'metadata'):
                user.metadata.status = 'suspended'
                user.metadata.save()
            else:
                UserMetaData.objects.create(
                    user=user,
                    status='suspended'
                )

        return JsonResponse({
            'success': True,
            'message': f'Student {user.get_full_name()} suspended successfully'
        })

    except Exception as e:
        logger.error(f"Error suspending student: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def reactivate_student(request, student_id):
    """Reactivate a suspended student"""
    from django.contrib.auth.models import User
    from lms.djangoapps.user_metadata.models import UserMetaData

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        # Verify student belongs to college
        try:
            college_student = CollegeStudent.objects.get(user_id=student_id, college=college)
        except CollegeStudent.DoesNotExist:
            return JsonResponse({'error': 'Student not found or does not belong to your university'}, status=404)

        user = college_student.user

        with transaction.atomic():
            user.is_active = True
            user.save()

            if hasattr(user, 'metadata'):
                user.metadata.status = 'active'
                user.metadata.save()
            else:
                UserMetaData.objects.create(
                    user=user,
                    status='active'
                )

        return JsonResponse({
            'success': True,
            'message': f'Student {user.get_full_name()} reactivated successfully'
        })

    except Exception as e:
        logger.error(f"Error reactivating student: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def archive_student(request, student_id):
    """Archive a student"""
    from lms.djangoapps.user_metadata.models import UserMetaData

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        # Verify student belongs to college
        try:
            college_student = CollegeStudent.objects.get(user_id=student_id, college=college)
        except CollegeStudent.DoesNotExist:
            return JsonResponse({'error': 'Student not found or does not belong to your university'}, status=404)

        user = college_student.user

        with transaction.atomic():
            if hasattr(user, 'metadata'):
                user.metadata.status = 'archived'
                user.metadata.save()
            else:
                UserMetaData.objects.create(
                    user=user,
                    status='archived'
                )

        return JsonResponse({
            'success': True,
            'message': f'Student {user.get_full_name()} archived successfully'
        })

    except Exception as e:
        logger.error(f"Error archiving student: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def bulk_move_section(request):
    """Bulk move students to a new programme/year/section"""
    import csv
    from io import StringIO
    from django.http import HttpResponse
    from lms.djangoapps.user_metadata.models import UserMetaData

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        programme_id = data.get('programme_id')
        year_name = data.get('year_name', '').strip()
        section_name = data.get('section_name', '').strip()

        if not student_ids:
            return JsonResponse({'error': 'No students selected'}, status=400)

        if not all([programme_id, year_name]):
            return JsonResponse({'error': 'Programme and year are required'}, status=400)

        # Verify programme belongs to college
        try:
            programme = UniversityProgrammes.objects.get(id=programme_id, university=college)
        except UniversityProgrammes.DoesNotExist:
            return JsonResponse({'error': 'Invalid programme'}, status=400)

        # Get programme year
        try:
            programme_year = UniversityProgrammesYear.objects.get(
                programme=programme,
                number_of_year=year_name
            )
        except UniversityProgrammesYear.DoesNotExist:
            return JsonResponse({'error': f'Year {year_name} not found for this programme'}, status=400)

        # Get programme section (optional)
        programme_section = None
        if section_name:
            try:
                programme_section = UniversityProgrammesYearSection.objects.get(
                    programme_year=programme_year,
                    name=section_name
                )
            except UniversityProgrammesYearSection.DoesNotExist:
                return JsonResponse({'error': f'Section {section_name} not found'}, status=400)

        success_count = 0
        failed_count = 0
        errors = []

        with transaction.atomic():
            for student_id in student_ids:
                try:
                    # Verify student belongs to college
                    college_student = CollegeStudent.objects.get(user_id=student_id, college=college)
                    user = college_student.user

                    # Get or update existing enrollment
                    enrolment = UniversityProgrammesEnrolment.objects.filter(
                        user=user,
                        is_active=True
                    ).first()

                    if enrolment:
                        # Update existing enrollment
                        enrolment.programme = programme
                        enrolment.programme_year = programme_year
                        enrolment.programme_section = programme_section
                        enrolment.save()
                    else:
                        # Create new enrollment
                        UniversityProgrammesEnrolment.objects.create(
                            user=user,
                            programme=programme,
                            programme_year=programme_year,
                            programme_section=programme_section,
                            is_active=True
                        )

                    success_count += 1

                except CollegeStudent.DoesNotExist:
                    failed_count += 1
                    errors.append(f'Student ID {student_id} not found')
                except Exception as e:
                    failed_count += 1
                    errors.append(f'Student ID {student_id}: {str(e)}')

        return JsonResponse({
            'success': True,
            'message': f'Successfully moved {success_count} student(s)',
            'success_count': success_count,
            'failed_count': failed_count,
            'errors': errors
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error in bulk move section: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def bulk_update_status(request):
    """Bulk update student status (suspend/reactivate/archive)"""
    from lms.djangoapps.user_metadata.models import UserMetaData

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        new_status = data.get('status', '').strip()

        if not student_ids:
            return JsonResponse({'error': 'No students selected'}, status=400)

        if new_status not in ['active', 'suspended', 'archived', 'inactive']:
            return JsonResponse({'error': 'Invalid status'}, status=400)

        success_count = 0
        failed_count = 0

        with transaction.atomic():
            for student_id in student_ids:
                try:
                    college_student = CollegeStudent.objects.get(user_id=student_id, college=college)
                    user = college_student.user

                    if hasattr(user, 'metadata'):
                        user.metadata.status = new_status
                        user.metadata.save()
                    else:
                        UserMetaData.objects.create(user=user, status=new_status)

                    success_count += 1

                except CollegeStudent.DoesNotExist:
                    failed_count += 1
                except Exception:
                    failed_count += 1

        status_action = {
            'suspended': 'suspended',
            'active': 'reactivated',
            'archived': 'archived',
            'inactive': 'deactivated'
        }.get(new_status, 'updated')

        return JsonResponse({
            'success': True,
            'message': f'Successfully {status_action} {success_count} student(s)',
            'success_count': success_count,
            'failed_count': failed_count
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error in bulk status update: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def bulk_export_csv(request):
    """Export selected students to CSV"""
    import csv
    from io import StringIO
    from django.http import HttpResponse
    from lms.djangoapps.user_metadata.models import UserMetaData

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])

        if not student_ids:
            return JsonResponse({'error': 'No students selected'}, status=400)

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="students_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'First Name', 'Last Name', 'Full Name', 'Email',
            'Programme', 'Year', 'Section', 'Status',
            'Student ID', 'Enrollment Number', 'Phone', 'University',
            'Date Joined'
        ])

        # Fetch students
        college_students = CollegeStudent.objects.filter(
            user_id__in=student_ids,
            college=college
        ).select_related('user', 'user__metadata').prefetch_related(
            Prefetch(
                'user__programme_enrolments',
                queryset=UniversityProgrammesEnrolment.objects.select_related(
                    'programme', 'programme_year', 'programme_section'
                ).filter(is_active=True)
            )
        )

        for cs in college_students:
            user = cs.user
            metadata = user.metadata if hasattr(user, 'metadata') else None
            enrolment = user.programme_enrolments.first() if user.programme_enrolments.exists() else None

            writer.writerow([
                user.id,
                user.first_name,
                user.last_name,
                user.get_full_name(),
                user.email,
                enrolment.programme.name if enrolment else '',
                enrolment.programme_year.number_of_year if enrolment and enrolment.programme_year else '',
                enrolment.programme_section.name if enrolment and enrolment.programme_section else '',
                metadata.status if metadata else 'inactive',
                metadata.student_id if metadata and hasattr(metadata, 'student_id') else '',
                metadata.enrollment_number if metadata and hasattr(metadata, 'enrollment_number') else '',
                metadata.phone if metadata and hasattr(metadata, 'phone') else '',
                college.name,
                user.date_joined.strftime('%Y-%m-%d %H:%M:%S') if user.date_joined else ''
            ])

        return response

    except Exception as e:
        logger.error(f"Error in bulk CSV export: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def bulk_delete_students(request):
    """Permanently delete selected students"""
    from django.contrib.auth.models import User
    from lms.djangoapps.user_metadata.models import UserMetaData

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])

        if not student_ids:
            return JsonResponse({'error': 'No students selected'}, status=400)

        success_count = 0
        failed_count = 0

        with transaction.atomic():
            for student_id in student_ids:
                try:
                    college_student = CollegeStudent.objects.get(user_id=student_id, college=college)
                    user = college_student.user

                    # Delete in order: enrollments, metadata, college_student, user
                    UniversityProgrammesEnrolment.objects.filter(user=user).delete()
                    if hasattr(user, 'metadata'):
                        user.metadata.delete()
                    college_student.delete()
                    user.delete()

                    success_count += 1

                except CollegeStudent.DoesNotExist:
                    failed_count += 1
                except Exception:
                    failed_count += 1

        return JsonResponse({
            'success': True,
            'message': f'Successfully deleted {success_count} student(s)',
            'success_count': success_count,
            'failed_count': failed_count
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error in bulk delete: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_student_overview_stats(request):
    """Get statistics for student overview page"""
    from django.contrib.auth.models import User
    from lms.djangoapps.user_metadata.models import UserMetaData
    from django.db.models import Count, Q

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        # Get all college students
        college_students = CollegeStudent.objects.filter(
            college=college
        ).select_related('user', 'user__metadata').prefetch_related(
            Prefetch(
                'user__programme_enrolments',
                queryset=UniversityProgrammesEnrolment.objects.select_related(
                    'programme'
                ).filter(is_active=True)
            )
        )

        total_students = college_students.count()

        # Count by status
        status_counts = {
            'active': 0,
            'suspended': 0,
            'pending': 0,
            'inactive': 0,
            'archived': 0
        }

        # Count by programme
        programme_stats = {}

        for cs in college_students:
            user = cs.user
            metadata = user.metadata if hasattr(user, 'metadata') else None
            status = metadata.status if metadata else 'inactive'

            # Increment status count
            if status in status_counts:
                status_counts[status] += 1

            # Get programme enrollment
            enrolment = user.programme_enrolments.first() if user.programme_enrolments.exists() else None

            if enrolment and enrolment.programme:
                prog_id = enrolment.programme.id
                if prog_id not in programme_stats:
                    programme_stats[prog_id] = {
                        'id': prog_id,
                        'name': enrolment.programme.name,
                        'short_name': enrolment.programme.short_name,
                        'color': enrolment.programme.color or '#1f4d3a',
                        'total': 0,
                        'active': 0,
                        'suspended': 0,
                        'pending': 0,
                        'inactive': 0,
                        'archived': 0
                    }

                programme_stats[prog_id]['total'] += 1
                if status in programme_stats[prog_id]:
                    programme_stats[prog_id][status] += 1

        # Get seat allocation info (you can customize this based on your college model)
        allocated_seats = college.allocated_seats if hasattr(college, 'allocated_seats') else 300
        used_seats = total_students - status_counts['archived']  # Archived don't use seats

        return JsonResponse({
            'success': True,
            'stats': {
                'total_students': total_students,
                'allocated_seats': allocated_seats,
                'used_seats': used_seats,
                'available_seats': allocated_seats - used_seats,
                'status_counts': status_counts,
                'programmes': list(programme_stats.values()),
                'transfers_used': 5,  # You can track this in a separate model
                'transfers_total': 10,
                'plan_name': 'EBC Standard Plan'
            }
        })

    except Exception as e:
        logger.error(f"Error getting overview stats: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# STUDENT IMPORT ENDPOINTS
# ============================================================================

@login_required
@require_http_methods(["GET"])
def download_student_template(request):
    """Download CSV template for student import"""
    import csv
    from django.http import HttpResponse

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_import_template.csv"'

    writer = csv.writer(response)

    # Write header - EXACTLY matches Add Student modal fields
    writer.writerow([
        'First Name',
        'Last Name',
        'Email',
        'Programme',
        'Year',
        'Section'
    ])

    # Write example rows
    writer.writerow([
        'Arjun',
        'Menon',
        'arjun.menon@example.com',
        'BA LLB',
        'Year 1',
        'Section A'
    ])
    writer.writerow([
        'Priya',
        'Nair',
        'priya.nair@example.com',
        'MBA',
        'Year 2',
        'Section B'
    ])
    writer.writerow([
        'Kavya',
        'Reddy',
        'kavya.reddy@example.com',
        'LLM',
        'Year 1',
        ''
    ])

    return response


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def import_students_csv(request):
    """
    Bulk import students from CSV file
    Process each row independently with detailed error reporting
    """
    import csv
    import io
    from lms.djangoapps.platform_admin.student_service import StudentService, StudentValidationError

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        # Get uploaded file
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

        csv_file = request.FILES['file']

        # Validate file type
        if not csv_file.name.endswith('.csv'):
            return JsonResponse({'error': 'Please upload a CSV file'}, status=400)

        # Read and decode file
        file_data = csv_file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(file_data))

        # Track results
        total_rows = 0
        success_count = 0
        failed_rows = []
        processed_emails = set()  # Track emails in this file to detect duplicates

        # Get all programmes for this college (for validation)
        programmes_map = {}
        for prog in UniversityProgrammes.objects.filter(university=college):
            # Map by both name and short_name
            programmes_map[prog.name.lower()] = prog.id
            programmes_map[prog.short_name.lower()] = prog.id

        # Process each row
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
            total_rows += 1

            try:
                # Extract and clean data
                first_name = row.get('First Name', '').strip()
                last_name = row.get('Last Name', '').strip()
                email = row.get('Email', '').strip().lower()
                programme_name = row.get('Programme', '').strip()
                year_name = row.get('Year', '').strip()
                section_name = row.get('Section', '').strip()

                # Validate required fields
                if not first_name:
                    raise StudentValidationError('First name is required')
                if not last_name:
                    raise StudentValidationError('Last name is required')
                if not email:
                    raise StudentValidationError('Email is required')
                if not programme_name:
                    raise StudentValidationError('Programme is required')
                if not year_name:
                    raise StudentValidationError('Year is required')

                # Check for duplicate email in uploaded file
                if email in processed_emails:
                    raise StudentValidationError(f'Duplicate email in file')

                processed_emails.add(email)

                # Map programme name to ID
                programme_key = programme_name.lower()
                if programme_key not in programmes_map:
                    raise StudentValidationError(f'Programme "{programme_name}" not found')

                programme_id = programmes_map[programme_key]

                # Create student using service (each row in its own transaction)
                result = StudentService.create_student(
                    college=college,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    programme_id=programme_id,
                    year_name=year_name,
                    section_name=section_name
                )

                success_count += 1

            except StudentValidationError as e:
                failed_rows.append({
                    'row': row_num,
                    'email': row.get('Email', ''),
                    'reason': str(e)
                })
            except Exception as e:
                logger.error(f"Error importing row {row_num}: {e}", exc_info=True)
                failed_rows.append({
                    'row': row_num,
                    'email': row.get('Email', ''),
                    'reason': f'Unexpected error: {str(e)}'
                })

        # Return detailed results
        return JsonResponse({
            'success': True,
            'total_rows': total_rows,
            'success_count': success_count,
            'failed_count': len(failed_rows),
            'failed_rows': failed_rows
        })

    except Exception as e:
        logger.error(f"Error importing students: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ========== Faculty Import Endpoints ==========

@login_required
@require_http_methods(["GET"])
def download_faculty_template(request):
    """Download CSV template for faculty import"""
    import csv
    from django.http import HttpResponse

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="faculty_import_template.csv"'

    writer = csv.writer(response)

    # Write header - matches Faculty Admin form fields
    writer.writerow([
        'First Name',
        'Last Name',
        'Email',
        'Faculty Type',
        'Programmes',
        'Placement Access'
    ])

    # Write example rows
    writer.writerow([
        'Priya',
        'Nair',
        'priya.nair@nlujai.ac.in',
        'teaching',
        'BA LLB;MBA',
        ''
    ])
    writer.writerow([
        'Vikram',
        'Reddy',
        'vikram.reddy@nlujai.ac.in',
        'placement',
        'MBA',
        'all_tracks'
    ])
    writer.writerow([
        'Anita',
        'Menon',
        'anita.menon@nlujai.ac.in',
        'placement',
        'LLM;BA LLB',
        'track_only'
    ])

    return response


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def import_faculty_csv(request):
    """
    Bulk import faculty from CSV file
    Validates seat availability before processing
    Creates CollegeStudent mapping for each faculty
    """
    import csv
    import io
    from lms.djangoapps.platform_admin.faculty_service import FacultyService, FacultyValidationError
    from lms.djangoapps.platform_admin.user_service import UserValidationError

    college = get_user_college(request.user)
    if not college:
        return JsonResponse({'error': 'User not associated with any university'}, status=403)

    try:
        # Get uploaded file
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

        csv_file = request.FILES['file']

        # Validate file type
        if not csv_file.name.endswith('.csv'):
            return JsonResponse({'error': 'Please upload a CSV file'}, status=400)

        # Read and decode file
        file_data = csv_file.read().decode('utf-8')

        # First pass: count NEW faculty members (exclude existing users)
        from django.contrib.auth import get_user_model
        User = get_user_model()

        csv_reader_count = csv.DictReader(io.StringIO(file_data))
        emails_to_import = []
        for row in csv_reader_count:
            email = row.get('Email', '').strip().lower()
            if email:
                emails_to_import.append(email)

        # Get existing users from the emails in CSV
        existing_users = User.objects.filter(email__in=emails_to_import).values_list('email', flat=True)
        existing_emails = set(existing_users)

        # Count only NEW faculty (users that don't exist yet)
        new_faculty_count = len([e for e in emails_to_import if e not in existing_emails])

        # Validate faculty seat availability BEFORE processing any records
        max_faculty = college.max_instructors if college.max_instructors else 0

        from lms.djangoapps.platform_admin.models import FacultyAdmin
        existing_faculty_users = FacultyAdmin.objects.filter(
            programmes__university=college,
            is_active=True
        ).values_list('user_id', flat=True).distinct()
        current_faculty_count = len(set(existing_faculty_users))

        available_seats = max_faculty - current_faculty_count if max_faculty > 0 else float('inf')

        # Check if import would exceed available seats (only count NEW faculty)
        if max_faculty > 0 and new_faculty_count > available_seats:
            return JsonResponse({
                'error': f'Faculty seats exceeded. You are trying to import {new_faculty_count} new faculty members, but only {int(available_seats)} seats are available. Maximum: {max_faculty}, Currently used: {current_faculty_count}. Note: {len(existing_emails)} users already exist and won\'t count against the quota. Please contact EBC Learning to upgrade your plan or reduce the number of new records.'
            }, status=400)

        # Reset file reader for actual processing
        csv_reader = csv.DictReader(io.StringIO(file_data))

        # Track results
        total_rows = 0
        success_count = 0
        failed_rows = []
        processed_emails = set()  # Track emails in this file to detect duplicates

        # Get all programmes for this college (for validation and lookup)
        programmes_map = {}
        for prog in UniversityProgrammes.objects.filter(university=college):
            # Map by both name and short_name
            programmes_map[prog.name.lower().strip()] = prog.id
            programmes_map[prog.short_name.lower().strip()] = prog.id

        # Process each row
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
            total_rows += 1

            try:
                # Extract and clean data
                first_name = row.get('First Name', '').strip()
                last_name = row.get('Last Name', '').strip()
                email = row.get('Email', '').strip().lower()
                faculty_type = row.get('Faculty Type', '').strip().lower()
                programmes_str = row.get('Programmes', '').strip()
                placement_access = row.get('Placement Access', '').strip().lower()

                # Validate required fields
                if not first_name:
                    raise FacultyValidationError('First name is required')
                if not last_name:
                    raise FacultyValidationError('Last name is required')
                if not email:
                    raise FacultyValidationError('Email is required')
                if not faculty_type:
                    raise FacultyValidationError('Faculty type is required')
                if not programmes_str:
                    raise FacultyValidationError('At least one programme is required')

                # Validate faculty type
                if faculty_type not in ['teaching', 'placement']:
                    raise FacultyValidationError(
                        f'Invalid faculty type "{faculty_type}". Must be "teaching" or "placement"'
                    )

                # Validate placement access for placement faculty
                if faculty_type == 'placement':
                    if not placement_access:
                        raise FacultyValidationError('Placement access is required for placement faculty')
                    if placement_access not in ['track_only', 'all_tracks']:
                        raise FacultyValidationError(
                            f'Invalid placement access "{placement_access}". Must be "track_only" or "all_tracks"'
                        )
                else:
                    # Teaching faculty should not have placement access
                    placement_access = None

                # Check for duplicate email in uploaded file
                if email in processed_emails:
                    raise FacultyValidationError('Duplicate email in file')

                processed_emails.add(email)

                # Parse programmes (semicolon-separated)
                programme_names = [p.strip() for p in programmes_str.replace(';', ',').split(',') if p.strip()]
                if not programme_names:
                    raise FacultyValidationError('At least one programme is required')

                # Map programme names to IDs
                programme_ids = []
                for prog_name in programme_names:
                    prog_key = prog_name.lower().strip()
                    if prog_key not in programmes_map:
                        raise FacultyValidationError(f'Programme "{prog_name}" not found')
                    programme_ids.append(programmes_map[prog_key])

                # Remove duplicates while preserving order
                seen = set()
                programme_ids = [x for x in programme_ids if not (x in seen or seen.add(x))]

                # Create faculty using service (each row in its own transaction)
                result = FacultyService.create_faculty_admin(
                    college=college,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    faculty_type=faculty_type,
                    programme_ids=programme_ids,
                    placement_access=placement_access if faculty_type == 'placement' else None
                )

                success_count += 1

            except (FacultyValidationError, UserValidationError) as e:
                # Validation or business logic error - add to failed rows
                failed_rows.append({
                    'row': row_num,
                    'first_name': row.get('First Name', ''),
                    'last_name': row.get('Last Name', ''),
                    'email': row.get('Email', ''),
                    'reason': str(e)
                })
                logger.warning(f"Row {row_num} failed validation: {str(e)}")

            except Exception as e:
                # Unexpected error
                failed_rows.append({
                    'row': row_num,
                    'first_name': row.get('First Name', ''),
                    'last_name': row.get('Last Name', ''),
                    'email': row.get('Email', ''),
                    'reason': f'Unexpected error: {str(e)}'
                })
                logger.error(f"Unexpected error processing row {row_num}: {e}", exc_info=True)

        # Return detailed results
        return JsonResponse({
            'success': True,
            'total_rows': total_rows,
            'success_count': success_count,
            'failed_count': len(failed_rows),
            'failed_rows': failed_rows
        })

    except Exception as e:
        logger.error(f"Error importing faculty: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ========== Faculty Admin API Endpoints ==========

@login_required
@csrf_exempt
@require_http_methods(["GET"])
def get_programmes_for_faculty(request):
    """
    Get programmes for faculty admin modal dropdown
    Returns programmes belonging to logged-in user's college
    """
    try:
        # Get user's college
        college = get_user_college(request.user)
        if not college:
            return JsonResponse({'error': 'No college associated with this user'}, status=403)

        # Get all programmes for this college
        programmes = UniversityProgrammes.objects.filter(
            university=college
        ).order_by('name').values('id', 'name', 'short_name')

        return JsonResponse({
            'success': True,
            'programmes': list(programmes)
        })

    except Exception as e:
        logger.error(f"Error loading programmes for faculty: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_faculty_admin(request):
    """
    Create a new faculty admin
    Creates User, UserMetaData, and FacultyAdmin records
    Assigns faculty to Admin group
    """
    from lms.djangoapps.platform_admin.faculty_service import FacultyService, FacultyValidationError

    try:
        # Get user's college
        college = get_user_college(request.user)
        if not college:
            return JsonResponse({'error': 'No college associated with this user'}, status=403)

        # Parse JSON request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # Extract fields
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip()
        faculty_type = data.get('faculty_type', '').strip()
        programme_ids = data.get('programme_ids', [])
        placement_access = data.get('placement_access', '').strip() if data.get('placement_access') else None

        # Use FacultyService to create faculty
        result = FacultyService.create_faculty_admin(
            college=college,
            first_name=first_name,
            last_name=last_name,
            email=email,
            faculty_type=faculty_type,
            programme_ids=programme_ids,
            placement_access=placement_access
        )

        logger.info(
            f"Faculty admin created: {email} by {request.user.username} "
            f"(created={result['was_created']})"
        )

        return JsonResponse({
            'success': True,
            'message': result['message'],
            'user_id': result['user_id'],
            'faculty_id': result['faculty_id'],
            'was_created': result['was_created']
        })

    except FacultyValidationError as e:
        logger.warning(f"Faculty validation failed: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

    except Exception as e:
        logger.error(f"Error creating faculty admin: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["GET"])
def list_faculty_admins(request):
    """
    List all faculty admins for the logged-in user's college
    Returns faculty with their programmes and details
    """
    try:
        # Get user's college
        college = get_user_college(request.user)
        if not college:
            return JsonResponse({'error': 'No college associated with this user'}, status=403)

        # Get all faculty admins for programmes in this college
        from lms.djangoapps.platform_admin.models import FacultyAdmin

        faculty_admins = FacultyAdmin.objects.filter(
            programmes__university=college,
            is_active=True
        ).select_related(
            'user',
            'user__profile'
        ).prefetch_related(
            'programmes'
        ).distinct().order_by('user__first_name', 'user__last_name')

        # Build response
        faculty_list = []
        for faculty in faculty_admins:
            # Get programme names
            programmes = faculty.programmes.filter(university=college)
            programme_names = ', '.join([p.name for p in programmes])
            programme_ids = [p.id for p in programmes]

            faculty_list.append({
                'id': faculty.id,
                'user_id': faculty.user.id,
                'name': f"{faculty.user.first_name} {faculty.user.last_name}",
                'email': faculty.user.email,
                'faculty_type': faculty.get_faculty_type_display(),
                'faculty_type_code': faculty.faculty_type,
                'programmes': programme_names,
                'programme_ids': programme_ids,
                'programme_count': programmes.count(),
                'placement_access': faculty.get_placement_access_display() if faculty.placement_access else '-',
                'placement_access_code': faculty.placement_access,
                'is_active': faculty.is_active,
                'created': faculty.created.strftime('%Y-%m-%d %H:%M:%S') if faculty.created else None
            })

        return JsonResponse({
            'success': True,
            'faculty_admins': faculty_list,
            'total_count': len(faculty_list)
        })

    except Exception as e:
        logger.error(f"Error listing faculty admins: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_faculty_admin(request, faculty_id):
    """Update faculty admin information"""
    from lms.djangoapps.platform_admin.models import FacultyAdmin

    try:
        college = get_user_college(request.user)
        if not college:
            return JsonResponse({'error': 'No college associated with this user'}, status=403)

        # Parse JSON request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # Get faculty admin
        try:
            faculty = FacultyAdmin.objects.get(id=faculty_id)
        except FacultyAdmin.DoesNotExist:
            return JsonResponse({'error': 'Faculty admin not found'}, status=404)

        # Verify faculty belongs to this college's programmes
        if not faculty.programmes.filter(university=college).exists():
            return JsonResponse({'error': 'Faculty admin does not belong to your university'}, status=403)

        # Get update data
        faculty_type = data.get('faculty_type')
        programme_ids = data.get('programme_ids', [])
        is_active = data.get('is_active', True)
        placement_access = data.get('placement_access')

        # Validate programmes belong to college
        if programme_ids:
            valid_programmes = UniversityProgrammes.objects.filter(
                id__in=programme_ids,
                university=college
            )
            if valid_programmes.count() != len(programme_ids):
                return JsonResponse({'error': 'Some programmes are invalid'}, status=400)

        with transaction.atomic():
            # Update faculty type
            if faculty_type:
                faculty.faculty_type = faculty_type

            # Update placement access
            if placement_access is not None:
                faculty.placement_access = placement_access

            # Update active status
            faculty.is_active = is_active
            faculty.save()

            # Update programmes
            if programme_ids:
                faculty.programmes.clear()
                faculty.programmes.add(*programme_ids)

        return JsonResponse({
            'success': True,
            'message': 'Faculty admin updated successfully'
        })

    except Exception as e:
        logger.error(f"Error updating faculty admin: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def promote_faculty_to_admin(request, faculty_id):
    """
    Promote a Faculty Admin to Institution Admin
    - Checks Institution Admin seat availability
    - Removes from FacultyAdmin
    - Adds to College.admin (Institution Admins)
    - Disables "Group Admin" (Faculty)
    - Enables "Organization Admin" (Institution Admin)
    """
    from lms.djangoapps.platform_admin.models import FacultyAdmin
    from django.contrib.auth.models import Group

    try:
        college = get_user_college(request.user)
        if not college:
            return JsonResponse({'error': 'No college associated with this user'}, status=403)

        # Check Institution Admin seat capacity
        max_admins = college.max_admins if college.max_admins else 0
        current_admin_count = college.admin.count()

        if max_admins > 0 and current_admin_count >= max_admins:
            return JsonResponse({
                'error': f'Institution Admin seats are full. Maximum: {max_admins}, Current: {current_admin_count}. Please contact EBC Learning to upgrade your plan.'
            }, status=400)

        # Get faculty admin
        try:
            faculty = FacultyAdmin.objects.get(id=faculty_id)
        except FacultyAdmin.DoesNotExist:
            return JsonResponse({'error': 'Faculty admin not found'}, status=404)

        # Verify faculty belongs to this college's programmes
        if not faculty.programmes.filter(university=college).exists():
            return JsonResponse({'error': 'Faculty admin does not belong to your university'}, status=403)

        user = faculty.user

        with transaction.atomic():
            # 1. Remove from FacultyAdmin (delete the record)
            faculty.delete()

            # 2. Add to College.admin (Institution Admins ManyToMany)
            college.admin.add(user)

            # 3. Update Django User Groups
            # DISABLE "Group Admin" (Faculty group)
            try:
                group_admin = Group.objects.get(name='Group Admin')
                if user.groups.filter(id=group_admin.id).exists():
                    user.groups.remove(group_admin)
                    logger.info(f"Removed {user.email} from Group Admin")
            except Group.DoesNotExist:
                logger.warning("Group Admin group does not exist")

            # Also remove from any other faculty-related groups
            faculty_groups = Group.objects.filter(name__icontains='faculty')
            for group in faculty_groups:
                if user.groups.filter(id=group.id).exists():
                    user.groups.remove(group)
                    logger.info(f"Removed {user.email} from {group.name}")

            # ENABLE "Organization Admin" (Institution Admin group)
            try:
                org_admin_group = Group.objects.get(name='Organization Admin')
                user.groups.add(org_admin_group)
                logger.info(f"Added {user.email} to Organization Admin")
            except Group.DoesNotExist:
                logger.warning("Organization Admin group does not exist")

            # Also try to add to "Institution Admin" if exists
            try:
                institution_admin_group = Group.objects.get(name='Institution Admin')
                user.groups.add(institution_admin_group)
                logger.info(f"Added {user.email} to Institution Admin")
            except Group.DoesNotExist:
                logger.warning("Institution Admin group does not exist")

            # Update user metadata
            if hasattr(user, 'metadata'):
                from lms.djangoapps.user_metadata.models import UserMetaData
                user.metadata.status = 'active'
                user.metadata.save()

        logger.info(
            f"Faculty {user.email} promoted to Institution Admin by {request.user.username}. "
            f"Admin seats: {current_admin_count + 1}/{max_admins}"
        )

        return JsonResponse({
            'success': True,
            'message': f'{user.get_full_name()} promoted to Institution Admin successfully',
            'admin_seats_used': current_admin_count + 1,
            'admin_seats_total': max_admins
        })

    except Exception as e:
        logger.error(f"Error promoting faculty to admin: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ========== Institution Admin API Endpoints ==========

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_institution_admin(request):
    """
    Create a new institution admin
    Creates User, UserMetaData, and InstitutionAdmin records
    """
    from lms.djangoapps.platform_admin.institution_service import InstitutionAdminService, InstitutionValidationError
    from lms.djangoapps.platform_admin.user_service import UserValidationError

    try:
        # Get user's college
        college = get_user_college(request.user)
        if not college:
            return JsonResponse({'error': 'No college associated with this user'}, status=403)

        # Parse JSON request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # Extract fields
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip()

        # Use InstitutionAdminService to create admin
        result = InstitutionAdminService.create_institution_admin(
            college=college,
            first_name=first_name,
            last_name=last_name,
            email=email
        )

        logger.info(
            f"Institution admin created: {email} by {request.user.username} "
            f"(created={result['was_created']})"
        )

        return JsonResponse({
            'success': True,
            'message': result['message'],
            'user_id': result['user_id'],
            'was_created': result['was_created']
        })

    except (InstitutionValidationError, UserValidationError) as e:
        logger.warning(f"Institution admin validation failed: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

    except Exception as e:
        logger.error(f"Error creating institution admin: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["GET"])
def list_institution_admins(request):
    """
    List all institution admins from college.admin ManyToMany field
    Returns institution admins with their details
    """
    try:
        # Get user's college
        college = get_user_college(request.user)
        if not college:
            return JsonResponse({'error': 'No college associated with this user'}, status=403)

        from django.contrib.auth.models import User

        # Get all users in college.admin ManyToMany field
        institution_admins = college.admin.filter(
            is_active=True
        ).select_related(
            'profile'
        ).prefetch_related(
            'metadata'
        ).order_by('first_name', 'last_name')

        # Build response
        admin_list = []
        for user in institution_admins:
            # Get user metadata for status
            try:
                metadata = user.metadata
                status = metadata.status if hasattr(metadata, 'status') else 'active'
            except:
                status = 'active'

            admin_list.append({
                'id': user.id,
                'user_id': user.id,
                'name': f"{user.first_name} {user.last_name}",
                'email': user.email,
                'is_active': user.is_active,
                'status': status,
                'created': user.date_joined.strftime('%Y-%m-%d %H:%M:%S') if user.date_joined else None
            })

        return JsonResponse({
            'success': True,
            'institution_admins': admin_list,
            'total_count': len(admin_list)
        })

    except Exception as e:
        logger.error(f"Error listing institution admins: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_institution_admin(request, admin_id):
    """
    Update institution admin details (name, status)
    """
    try:
        # Get user's college
        college = get_user_college(request.user)
        if not college:
            return JsonResponse({'error': 'No college associated with this user'}, status=403)

        from django.contrib.auth.models import User

        # Get the admin user
        try:
            admin_user = User.objects.get(id=admin_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Institution admin not found'}, status=404)

        # Verify this user is an institution admin in this college
        if not college.admin.filter(id=admin_id).exists():
            return JsonResponse({'error': 'User is not an institution admin in your college'}, status=403)

        # Parse JSON request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # Extract fields
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        status = data.get('status', '').strip()

        # Validate required fields
        if not first_name or not last_name:
            return JsonResponse({'error': 'First name and last name are required'}, status=400)

        if status and status not in ['active', 'suspended', 'pending']:
            return JsonResponse({'error': 'Invalid status value'}, status=400)

        with transaction.atomic():
            # Update user name
            admin_user.first_name = first_name
            admin_user.last_name = last_name
            admin_user.save()

            # Update profile name
            if hasattr(admin_user, 'profile'):
                admin_user.profile.name = f"{first_name} {last_name}"
                admin_user.profile.save()

            # Update metadata status if provided
            if status:
                try:
                    metadata = admin_user.metadata
                    metadata.status = status
                    metadata.save()
                except:
                    # Create metadata if doesn't exist
                    from lms.djangoapps.user_metadata.models import UserMetaData
                    UserMetaData.objects.create(
                        user=admin_user,
                        status=status,
                        studio=True,
                        careers_app=True
                    )

        logger.info(f"Institution admin updated: {admin_user.email} by {request.user.username}")

        return JsonResponse({
            'success': True,
            'message': 'Institution Admin updated successfully'
        })

    except Exception as e:
        logger.error(f"Error updating institution admin: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ========== Seat Management API Endpoints ==========

@login_required
@csrf_exempt
@require_http_methods(["GET"])
def get_seat_management_data(request):
    """
    Get seat management data including:
    - University total seats
    - All programmes with allocated and occupied seats
    - Student counts by status
    """
    try:
        # Get user's college
        college = get_user_college(request.user)
        if not college:
            return JsonResponse({'error': 'No college associated with this user'}, status=403)

        # Get university total seats
        university_total_seats = college.max_students

        # Get all programmes for this college with student counts
        programmes = UniversityProgrammes.objects.filter(
            university=college,
            status='active'
        ).select_related('university').prefetch_related(
            'universityprogrammesenrolment_set__user__metadata'
        ).order_by('short_name')

        programme_data = []
        total_active = 0
        total_suspended = 0
        total_pending = 0
        total_inactive = 0

        for programme in programmes:
            # Get all enrolled students for this programme
            enrolments = programme.universityprogrammesenrolment_set.filter(is_active=True)

            # Count students by status
            active_count = 0
            suspended_count = 0
            pending_count = 0
            inactive_count = 0

            for enrolment in enrolments:
                try:
                    user_metadata = enrolment.user.metadata
                    status = user_metadata.status if hasattr(user_metadata, 'status') else 'active'

                    if status == 'active':
                        active_count += 1
                    elif status == 'suspended':
                        suspended_count += 1
                    elif status == 'pending':
                        pending_count += 1
                    elif status == 'inactive':
                        inactive_count += 1
                except:
                    # If no metadata, treat as active
                    active_count += 1

            # Total occupied seats (active + suspended + pending)
            occupied_seats = active_count + suspended_count + pending_count

            # Add to totals
            total_active += active_count
            total_suspended += suspended_count
            total_pending += pending_count
            total_inactive += inactive_count

            programme_data.append({
                'id': programme.id,
                'name': programme.name,
                'short_name': programme.short_name,
                'color': programme.color or '#A31F36',
                'allocated_seats': programme.allocated_seats,
                'occupied_seats': occupied_seats,
                'duration': programme.get_duration_years() if hasattr(programme, 'get_duration_years') else 5,
                'students': {
                    'active': active_count,
                    'suspended': suspended_count,
                    'pending': pending_count,
                    'inactive': inactive_count
                }
            })

        # Get institution admin and faculty counts
        institution_admin_count = college.admin.count()

        from lms.djangoapps.platform_admin.models import FacultyAdmin
        faculty_count = FacultyAdmin.objects.filter(
            programmes__university=college,
            is_active=True
        ).values_list('user_id', flat=True).distinct().count()

        return JsonResponse({
            'success': True,
            'university': {
                'name': college.name,
                'total_seats': university_total_seats
            },
            'college': {
                'max_admins': college.max_admins or 0,
                'max_instructors': college.max_instructors or 0,
                'institution_admin_count': institution_admin_count,
                'faculty_count': faculty_count
            },
            'programmes': programme_data,
            'summary': {
                'total_active': total_active,
                'total_suspended': total_suspended,
                'total_pending': total_pending,
                'total_inactive': total_inactive,
                'total_occupied': total_active + total_suspended + total_pending
            }
        })

    except Exception as e:
        logger.error(f"Error getting seat management data: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_programme_seat_allocations(request):
    """
    Update seat allocations for multiple programmes
    Validates:
    - Total allocated seats cannot exceed university total seats
    - Programme seats cannot be reduced below currently occupied seats
    """
    try:
        # Get user's college
        college = get_user_college(request.user)
        if not college:
            return JsonResponse({'error': 'No college associated with this user'}, status=403)

        # Parse request data
        data = json.loads(request.body)
        allocations = data.get('allocations', [])  # [{programme_id: int, allocated_seats: int}]

        if not allocations:
            return JsonResponse({'error': 'No allocations provided'}, status=400)

        # Get university total seats
        university_total_seats = college.max_students

        # Validation errors
        validation_errors = []

        # Calculate total allocated seats
        total_allocated = sum(alloc['allocated_seats'] for alloc in allocations)

        # Validation 1: Total allocated must exactly equal university total
        if total_allocated != university_total_seats:
            if total_allocated > university_total_seats:
                over_by = total_allocated - university_total_seats
                return JsonResponse({
                    'success': False,
                    'error': f'Total allocated programme seats ({total_allocated}) exceed university total seats ({university_total_seats}) by {over_by} seats.'
                }, status=400)
            else:
                remaining = university_total_seats - total_allocated
                return JsonResponse({
                    'success': False,
                    'error': f'Total allocated programme seats ({total_allocated}) must equal university total seats ({university_total_seats}). {remaining} seats remain unallocated.'
                }, status=400)

        # Validation 2: Check each programme individually
        programmes_to_update = []
        for alloc in allocations:
            programme_id = alloc.get('programme_id')
            allocated_seats = alloc.get('allocated_seats')

            # Validate data types
            if not isinstance(programme_id, int) or not isinstance(allocated_seats, int):
                validation_errors.append(f'Invalid data type for programme {programme_id}')
                continue

            # Validate non-negative
            if allocated_seats < 0:
                validation_errors.append(f'Allocated seats cannot be negative for programme {programme_id}')
                continue

            # Get programme
            try:
                programme = UniversityProgrammes.objects.select_related('university').get(
                    id=programme_id,
                    university=college
                )
            except UniversityProgrammes.DoesNotExist:
                validation_errors.append(f'Programme {programme_id} not found or does not belong to your university')
                continue

            # Get current occupied seats
            enrolments = programme.universityprogrammesenrolment_set.filter(is_active=True)

            occupied_seats = 0
            for enrolment in enrolments:
                try:
                    user_metadata = enrolment.user.metadata
                    status = user_metadata.status if hasattr(user_metadata, 'status') else 'active'

                    # Count active, suspended, and pending as occupied
                    if status in ['active', 'suspended', 'pending']:
                        occupied_seats += 1
                except:
                    # If no metadata, treat as active (occupied)
                    occupied_seats += 1

            # Validation: Cannot reduce below occupied seats
            if allocated_seats < occupied_seats:
                validation_errors.append({
                    'programme_id': programme_id,
                    'programme_name': programme.short_name,
                    'allocated_seats': allocated_seats,
                    'occupied_seats': occupied_seats,
                    'error': f'Cannot reduce {programme.short_name} seats to {allocated_seats}. Currently {occupied_seats} students are enrolled.'
                })
                continue

            programmes_to_update.append({
                'programme': programme,
                'allocated_seats': allocated_seats
            })

        # If there are validation errors, return them
        if validation_errors:
            return JsonResponse({
                'success': False,
                'validation_errors': validation_errors
            }, status=400)

        # All validations passed - update in a transaction
        with transaction.atomic():
            for item in programmes_to_update:
                programme = item['programme']
                programme.allocated_seats = item['allocated_seats']
                programme.save()

        return JsonResponse({
            'success': True,
            'message': f'Successfully updated seat allocations for {len(programmes_to_update)} programme(s)',
            'updated_count': len(programmes_to_update)
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error updating programme seat allocations: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ========== Platform Admin Overview/Dashboard API Endpoint ==========

@login_required
@csrf_exempt
@require_http_methods(["GET"])
def get_platform_overview(request):
    """
    Get comprehensive platform admin overview data including:
    - University/Institution details
    - Total users, students, faculty, admins count
    - Seat usage statistics
    - Programme list with student counts
    - App enablement status per programme
    """
    try:
        # Get user's college
        college = get_user_college(request.user)
        if not college:
            return JsonResponse({'error': 'No college associated with this user'}, status=403)

        # University details
        # Extract short name intelligently (e.g., "NLU Jaipur" from "National Law University, Jaipur")
        short_name = college.name.split()[0] if college.name else ''
        if college.name:
            # If name contains comma, take part before comma and extract acronym
            if ',' in college.name:
                main_part = college.name.split(',')[0].strip()
                # Create acronym from main part
                words = main_part.split()
                if len(words) > 1:
                    short_name = ''.join([w[0].upper() for w in words if w])
                    # Add location if present after comma
                    location = college.name.split(',')[1].strip() if len(college.name.split(',')) > 1 else ''
                    if location:
                        short_name = short_name + ' ' + location
            else:
                # Just use first word if no comma
                short_name = college.name.split()[0]

        university_data = {
            'name': college.name,
            'short_name': short_name,
            'logo_initial': college.name[0].upper() if college.name else 'U',
            'total_seats': college.max_students,
            'plan': 'EBC Standard Plan'
        }

        # Get all active programmes
        programmes = UniversityProgrammes.objects.filter(
            university=college,
            status='active'
        ).prefetch_related(
            'universityprogrammesenrolment_set__user__metadata'
        ).order_by('short_name')

        programme_list = []
        total_students = 0
        total_active_students = 0
        mystudio_enabled_programmes = 0
        careers_enabled_programmes = 0

        for programme in programmes:
            # Get all active enrollments for this programme
            enrolments = programme.universityprogrammesenrolment_set.filter(is_active=True)

            active_count = 0
            suspended_count = 0
            pending_count = 0

            for enrolment in enrolments:
                try:
                    user_metadata = enrolment.user.metadata
                    status = user_metadata.status if hasattr(user_metadata, 'status') else 'active'

                    if status == 'active':
                        active_count += 1
                    elif status == 'suspended':
                        suspended_count += 1
                    elif status == 'pending':
                        pending_count += 1
                except:
                    active_count += 1

            occupied_seats = active_count + suspended_count + pending_count
            total_students += occupied_seats
            total_active_students += active_count

            # Count enabled apps
            if programme.enable_mystudio:
                mystudio_enabled_programmes += 1
            if programme.enable_careers_app:
                careers_enabled_programmes += 1

            programme_list.append({
                'id': programme.id,
                'name': programme.name,
                'short_name': programme.short_name,
                'color': programme.color or '#A31F36',
                'student_count': occupied_seats,
                'active_students': active_count,
                'allocated_seats': programme.allocated_seats,
                'enable_mystudio': programme.enable_mystudio,
                'enable_careers_app': programme.enable_careers_app
            })

        # Count faculty admins
        from lms.djangoapps.platform_admin.models import FacultyAdmin
        faculty_count = FacultyAdmin.objects.filter(
            programmes__university=college,
            is_active=True
        ).distinct().count()

        # Count institution admins (users in "Organization" group for this college)
        from django.contrib.auth.models import Group
        try:
            org_group = Group.objects.get(name='Organization')
            institution_admin_count = User.objects.filter(
                groups=org_group,
                collegestudent__college=college
            ).count()
        except:
            institution_admin_count = 0

        # Total users
        total_users = total_students + faculty_count + institution_admin_count

        # Seats usage
        seats_in_use = total_students
        seats_available = university_data['total_seats'] - seats_in_use
        utilization_percent = round((seats_in_use / university_data['total_seats'] * 100), 1) if university_data['total_seats'] > 0 else 0

        # Apps summary
        active_apps = []
        if mystudio_enabled_programmes > 0:
            active_apps.append('MyStudio')
        if careers_enabled_programmes > 0:
            active_apps.append('Careers App')

        return JsonResponse({
            'success': True,
            'university': university_data,
            'stats': {
                'total_users': total_users,
                'total_students': total_students,
                'active_students': total_active_students,
                'faculty_count': faculty_count,
                'institution_admin_count': institution_admin_count,
                'seats_in_use': seats_in_use,
                'seats_available': seats_available,
                'utilization_percent': utilization_percent,
                'programme_count': len(programme_list),
                'active_apps_count': len(active_apps),
                'active_apps': active_apps
            },
            'programmes': programme_list,
            'apps': {
                'mystudio': {
                    'enabled': mystudio_enabled_programmes > 0,
                    'programme_count': mystudio_enabled_programmes
                },
                'careers': {
                    'enabled': careers_enabled_programmes > 0,
                    'programme_count': careers_enabled_programmes
                }
            }
        })

    except Exception as e:
        logger.error(f"Error getting platform overview: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_staff_overview(request):
    """
    Get staff overview data for Platform Admin
    Returns statistics about faculty and institution admins
    """
    from django.contrib.auth.models import Group
    from lms.djangoapps.platform_admin.models import FacultyAdmin

    try:
        college = get_user_college(request.user)
        if not college:
            return JsonResponse({'error': 'No college associated with this user'}, status=403)

        # Get max seats from College model
        max_faculty = college.max_instructors if college.max_instructors else 0
        max_institution_admins = college.max_admins if college.max_admins else 0

        # Count actual Faculty Admins (from FacultyAdmin model)
        faculty_count = FacultyAdmin.objects.filter(
            user__faculty_admin__isnull=False
        ).select_related('user').filter(
            programmes__university=college
        ).distinct().count()

        # Count Institution Admins (from College.admin ManyToMany field)
        institution_admin_count = college.admin.count()

        # Total staff
        total_staff = faculty_count + institution_admin_count

        # Faculty by programme
        programmes = UniversityProgrammes.objects.filter(
            university=college,
            status='active'
        ).prefetch_related('faculty_admins').order_by('short_name')

        faculty_by_programme = []
        for programme in programmes:
            faculty_in_programme = programme.faculty_admins.count()
            if faculty_in_programme > 0:
                faculty_by_programme.append({
                    'programme_name': programme.name,
                    'short_name': programme.short_name,
                    'faculty_count': faculty_in_programme,
                    'color': programme.color or '#1f4d3a'
                })

        # Faculty by type (teaching vs placement)
        teaching_faculty_count = FacultyAdmin.objects.filter(
            programmes__university=college,
            faculty_type='teaching'
        ).distinct().count()

        placement_faculty_count = FacultyAdmin.objects.filter(
            programmes__university=college,
            faculty_type='placement'
        ).distinct().count()

        # Get all staff members (Institution Admins + Faculty Admins)
        all_staff = []

        # Add Institution Admins
        for admin_user in college.admin.all():
            all_staff.append({
                'id': admin_user.id,
                'name': admin_user.get_full_name() or admin_user.username,
                'email': admin_user.email,
                'type': 'institution_admin',
                'type_label': 'Institution Admin',
                'faculty_type': None,
                'programmes': [],
                'status': 'active',
                'initials': ''.join([n[0].upper() for n in (admin_user.get_full_name() or admin_user.username).split()[:2]])
            })

        # Add Faculty Admins
        faculty_admins = FacultyAdmin.objects.filter(
            programmes__university=college
        ).select_related('user').prefetch_related('programmes').distinct()

        for faculty in faculty_admins:
            user = faculty.user
            faculty_programmes = faculty.programmes.filter(university=college)

            all_staff.append({
                'id': user.id,
                'name': user.get_full_name() or user.username,
                'email': user.email,
                'type': 'faculty_admin',
                'type_label': 'Teaching Faculty' if faculty.faculty_type == 'teaching' else 'Placement Faculty',
                'faculty_type': faculty.faculty_type,
                'programmes': [
                    {
                        'name': prog.name,
                        'short_name': prog.short_name,
                        'color': prog.color or '#1f4d3a'
                    }
                    for prog in faculty_programmes
                ],
                'status': 'active',
                'initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]])
            })

        return JsonResponse({
            'success': True,
            'max_faculty': max_faculty,
            'max_institution_admins': max_institution_admins,
            'faculty_count': faculty_count,
            'institution_admin_count': institution_admin_count,
            'total_staff': total_staff,
            'faculty_seats_available': max(0, max_faculty - faculty_count),
            'admin_seats_available': max(0, max_institution_admins - institution_admin_count),
            'faculty_by_programme': faculty_by_programme,
            'faculty_by_type': {
                'teaching': teaching_faculty_count,
                'placement': placement_faculty_count
            },
            'all_staff': all_staff
        })

    except Exception as e:
        logger.error(f"Error getting staff overview: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
