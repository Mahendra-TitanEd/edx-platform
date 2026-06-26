"""
Faculty Admin Service Module
Reusable business logic for faculty admin creation and validation
"""

import logging
from django.db import transaction
from lms.djangoapps.platform_admin.user_service import UserService, UserValidationError
from lms.djangoapps.platform_admin.models import FacultyAdmin
from lms.djangoapps.university_programme.models import UniversityProgrammes

logger = logging.getLogger(__name__)


class FacultyValidationError(Exception):
    """Custom exception for faculty validation errors"""
    pass


class FacultyService:
    """
    Service class for faculty admin management operations
    Provides reusable methods for creating faculty and validating assignments
    """


    @staticmethod
    def validate_programmes(programme_ids, college):
        """
        Validate that programmes exist and belong to college

        Args:
            programme_ids: List of programme IDs
            college: College instance

        Returns:
            List of UniversityProgrammes instances

        Raises:
            FacultyValidationError: If any programme is invalid
        """
        if not programme_ids:
            raise FacultyValidationError('At least one programme must be selected')

        programmes = []
        for prog_id in programme_ids:
            try:
                programme = UniversityProgrammes.objects.get(
                    id=prog_id,
                    university=college
                )
                programmes.append(programme)
            except UniversityProgrammes.DoesNotExist:
                raise FacultyValidationError(f'Invalid programme ID: {prog_id}')

        return programmes

    @staticmethod
    def check_duplicate_faculty(user, programme_ids):
        """
        Check if user is already a faculty admin for any of the programmes

        Args:
            user: User instance
            programme_ids: List of programme IDs

        Raises:
            FacultyValidationError: If faculty already assigned to a programme
        """
        # Check if FacultyAdmin record exists for this user
        try:
            faculty = FacultyAdmin.objects.get(user=user)

            # Check if user is already assigned to any of the requested programmes
            existing_programmes = faculty.programmes.filter(id__in=programme_ids)
            if existing_programmes.exists():
                prog_names = ', '.join([p.name for p in existing_programmes])
                raise FacultyValidationError(
                    f'User is already a faculty admin for: {prog_names}'
                )
        except FacultyAdmin.DoesNotExist:
            # No existing faculty record, OK to proceed
            pass


    @staticmethod
    def create_or_update_faculty_admin(user, faculty_type, programmes, placement_access=None):
        """
        Create or update FacultyAdmin record

        Args:
            user: User instance
            faculty_type: 'teaching' or 'placement'
            programmes: List of UniversityProgrammes instances
            placement_access: 'track_only' or 'all_tracks' (required for placement)

        Returns:
            FacultyAdmin instance
        """
        # Get or create FacultyAdmin
        faculty, created = FacultyAdmin.objects.get_or_create(
            user=user,
            defaults={
                'faculty_type': faculty_type,
                'placement_access': placement_access if faculty_type == 'placement' else None,
                'is_active': True
            }
        )

        if not created:
            # Update existing record
            faculty.faculty_type = faculty_type
            faculty.placement_access = placement_access if faculty_type == 'placement' else None
            faculty.is_active = True
            faculty.save()

        # Set programmes (this replaces existing)
        faculty.programmes.set(programmes)

        return faculty

    @classmethod
    def create_faculty_admin(cls, college, first_name, last_name, email, faculty_type,
                            programme_ids, placement_access=None):
        """
        Complete faculty admin creation workflow
        Validates all inputs and creates all necessary records

        Args:
            college: College instance
            first_name: Faculty first name
            last_name: Faculty last name
            email: Faculty email
            faculty_type: 'teaching' or 'placement'
            programme_ids: List of programme IDs
            placement_access: 'track_only' or 'all_tracks' (optional)

        Returns:
            dict: {'user_id': int, 'was_created': bool, 'message': str}

        Raises:
            FacultyValidationError: If any validation fails
        """
        # Validate inputs
        first_name = first_name.strip()
        last_name = last_name.strip()
        email = email.strip().lower()

        # Validate required fields
        UserService.validate_required_fields({
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'faculty_type': faculty_type,
            'programmes': programme_ids
        })

        # Validate email format
        UserService.validate_email_format(email)

        # Validate faculty type
        if faculty_type not in ['teaching', 'placement']:
            raise FacultyValidationError('Invalid faculty type')

        # Validate placement access if placement faculty
        if faculty_type == 'placement':
            if not placement_access:
                raise FacultyValidationError('Placement access is required for placement faculty')
            if placement_access not in ['track_only', 'all_tracks']:
                raise FacultyValidationError('Invalid placement access value')

        # Validate programmes belong to college
        programmes = cls.validate_programmes(programme_ids, college)

        # Check faculty seat availability
        max_faculty = college.max_instructors if college.max_instructors else 0

        # Count existing faculty (only count unique users, not FacultyAdmin records)
        from lms.djangoapps.platform_admin.models import FacultyAdmin
        existing_faculty_users = FacultyAdmin.objects.filter(
            programmes__university=college,
            is_active=True
        ).values_list('user_id', flat=True).distinct()
        current_faculty_count = len(set(existing_faculty_users))

        # Check if adding new faculty (not updating existing)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        existing_user = User.objects.filter(email=email).first()

        # Only count against quota if this is a NEW faculty member
        if not existing_user or existing_user.id not in existing_faculty_users:
            if max_faculty > 0 and current_faculty_count >= max_faculty:
                raise FacultyValidationError(
                    f'Faculty seats are full. Maximum: {max_faculty}, Current: {current_faculty_count}. '
                    f'Please contact EBC Learning to upgrade your plan.'
                )

        # Create all records in transaction
        with transaction.atomic():
            # Step 1: Get or create user
            user, was_created = UserService.get_or_create_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                update_name=True
            )

            # Step 2: Map user to college/university (like students in CollegeStudent table)
            from college.models import CollegeStudent
            college_student, cs_created = CollegeStudent.objects.get_or_create(
                user=user,
                defaults={'college': college}
            )

            # If record exists but college is different, update it
            if not cs_created and college_student.college != college:
                college_student.college = college
                college_student.save()
                logger.info(f"Updated college mapping for {user.email} from {college_student.college.name} to {college.name}")

            # Step 3: Assign to Admin group (for faculty)
            UserService.assign_to_group(user, 'Admin')

            # Step 4: Get or create user metadata
            # Set studio/careers_app based on faculty type
            studio = (faculty_type == 'teaching')
            careers_app = (faculty_type == 'placement')
            UserService.get_or_create_user_metadata(
                user=user,
                status='active',
                studio=studio,
                careers_app=careers_app
            )

            # Step 5: Check for duplicate faculty assignment
            cls.check_duplicate_faculty(user, programme_ids)

            # Step 6: Create or update faculty admin
            faculty = cls.create_or_update_faculty_admin(
                user=user,
                faculty_type=faculty_type,
                programmes=programmes,
                placement_access=placement_access
            )

        return {
            'user_id': user.id,
            'faculty_id': faculty.id,
            'was_created': was_created,
            'message': 'Faculty Admin created successfully'
        }
