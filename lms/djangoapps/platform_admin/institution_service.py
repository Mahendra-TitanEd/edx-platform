"""
Institution Admin Service Module
Reusable business logic for institution admin creation and validation
Institution admins are identified by "Organization" group membership
"""

import logging
from django.db import transaction
from django.contrib.auth.models import Group
from lms.djangoapps.platform_admin.user_service import UserService, UserValidationError

logger = logging.getLogger(__name__)

# Group name for Institution Admins
ORGANIZATION_GROUP = 'Organization'


class InstitutionValidationError(Exception):
    """Custom exception for institution admin validation errors"""
    pass


class InstitutionAdminService:
    """
    Service class for institution admin management operations
    Provides reusable methods for creating institution admins
    Institution admins are identified by Organization group membership
    """

    @staticmethod
    def check_duplicate_institution_admin(user):
        """
        Check if user is already an institution admin (has Organization group)

        Args:
            user: User instance

        Raises:
            InstitutionValidationError: If user is already an institution admin
        """
        try:
            org_group = Group.objects.get(name=ORGANIZATION_GROUP)
            if user.groups.filter(id=org_group.id).exists():
                raise InstitutionValidationError(
                    f'User {user.email} is already an institution admin'
                )
        except Group.DoesNotExist:
            # Group doesn't exist yet, so user can't be in it
            pass

    @classmethod
    def create_institution_admin(cls, college, first_name, last_name, email):
        """
        Complete institution admin creation workflow
        Validates all inputs and creates all necessary records
        Assigns user to Organization group

        Args:
            college: College instance (for validation/logging)
            first_name: Admin first name
            last_name: Admin last name
            email: Admin email

        Returns:
            dict: {'user_id': int, 'was_created': bool, 'message': str}

        Raises:
            InstitutionValidationError: If any validation fails
            UserValidationError: If user validation fails
        """
        # Validate inputs
        first_name = first_name.strip()
        last_name = last_name.strip()
        email = email.strip().lower()

        # Validate required fields
        UserService.validate_required_fields({
            'first_name': first_name,
            'last_name': last_name,
            'email': email
        })

        # Validate email format
        UserService.validate_email_format(email)

        # Check institution admin seat availability
        max_admins = college.max_admins if college.max_admins else 0
        current_admin_count = college.admin.count()

        # Only count against quota if this is a NEW admin
        from django.contrib.auth import get_user_model
        User = get_user_model()
        existing_user = User.objects.filter(email=email).first()

        # Check if existing user is already an institution admin
        is_existing_admin = False
        if existing_user:
            is_existing_admin = college.admin.filter(id=existing_user.id).exists()

        # Only validate seat availability for new admins
        if not is_existing_admin:
            if max_admins > 0 and current_admin_count >= max_admins:
                raise InstitutionValidationError(
                    f'Institution Admin seats are full. Maximum: {max_admins}, Current: {current_admin_count}. '
                    f'Please contact EBC Learning to upgrade your plan.'
                )

        # Create all records in transaction
        with transaction.atomic():
            # Step 1: Get or create user
            user, user_was_created = UserService.get_or_create_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                update_name=True
            )

            # Step 2: Map user to college/university (like students and faculty in CollegeStudent table)
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

            # Step 3: Get or create user metadata
            # Institution admins get full access: studio=True, careers_app=True
            UserService.get_or_create_user_metadata(
                user=user,
                status='active',
                studio=True,
                careers_app=True
            )

            # Step 4: Check for duplicate institution admin
            cls.check_duplicate_institution_admin(user)

            # Step 5: Assign to Organization group
            UserService.assign_to_group(user, ORGANIZATION_GROUP)

            # Step 6: Add to College.admin ManyToMany field
            college.admin.add(user)

        return {
            'user_id': user.id,
            'was_created': user_was_created,
            'message': 'Institution Admin created successfully'
        }
