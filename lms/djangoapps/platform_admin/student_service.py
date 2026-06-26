"""
Student Service Module
Reusable business logic for student creation and validation
Shared between Add Student and Import Students features
"""

import logging
from django.db import transaction
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from common.djangoapps.student.models import Registration, UserProfile
from lms.djangoapps.user_metadata.models import UserMetaData
from lms.djangoapps.university_programme.models import (
    UniversityProgrammes,
    UniversityProgrammesYear,
    UniversityProgrammesYearSection,
    UniversityProgrammesEnrolment
)
from college.models import CollegeStudent

logger = logging.getLogger(__name__)


class StudentValidationError(Exception):
    """Custom exception for student validation errors"""
    pass


class StudentService:
    """
    Service class for student management operations
    Provides reusable methods for creating students and validating enrollments
    """

    @staticmethod
    def validate_email_format(email):
        """
        Validate email format

        Args:
            email: Email address string

        Raises:
            StudentValidationError: If email format is invalid
        """
        try:
            validate_email(email)
        except ValidationError:
            raise StudentValidationError('Invalid email format')

    @staticmethod
    def validate_programme(programme_id, college):
        """
        Validate that programme exists and belongs to college

        Args:
            programme_id: Programme ID
            college: College instance

        Returns:
            UniversityProgrammes instance

        Raises:
            StudentValidationError: If programme is invalid
        """
        try:
            programme = UniversityProgrammes.objects.get(
                id=programme_id,
                university=college
            )
            return programme
        except UniversityProgrammes.DoesNotExist:
            raise StudentValidationError('Invalid programme')

    @staticmethod
    def validate_programme_year(programme, year_name):
        """
        Validate that year exists for the programme

        Args:
            programme: UniversityProgrammes instance
            year_name: Year name string

        Returns:
            UniversityProgrammesYear instance

        Raises:
            StudentValidationError: If year is invalid
        """
        try:
            programme_year = UniversityProgrammesYear.objects.get(
                programme=programme,
                number_of_year=year_name
            )
            return programme_year
        except UniversityProgrammesYear.DoesNotExist:
            raise StudentValidationError(f'Year {year_name} not found for this programme')

    @staticmethod
    def validate_programme_section(programme_year, section_name):
        """
        Validate that section exists for the year (if section provided)

        Args:
            programme_year: UniversityProgrammesYear instance
            section_name: Section name string (can be empty)

        Returns:
            UniversityProgrammesYearSection instance or None

        Raises:
            StudentValidationError: If section is invalid
        """
        if not section_name:
            return None

        try:
            programme_section = UniversityProgrammesYearSection.objects.get(
                programme_year=programme_year,
                name=section_name
            )
            return programme_section
        except UniversityProgrammesYearSection.DoesNotExist:
            raise StudentValidationError(
                f'Section {section_name} not found for {programme_year.number_of_year}'
            )

    @staticmethod
    def check_seat_availability(programme):
        """
        Check if programme has available seats

        Args:
            programme: UniversityProgrammes instance

        Returns:
            tuple: (bool, int, int) - (has_seats, used_seats, allocated_seats)

        Raises:
            StudentValidationError: If seats are full
        """
        # Get allocated seats for programme
        allocated_seats = programme.allocated_seats if hasattr(programme, 'allocated_seats') and programme.allocated_seats else None

        if allocated_seats is None:
            # No seat limit configured
            return True, 0, 0

        # Count active enrollments for this programme
        used_seats = UniversityProgrammesEnrolment.objects.filter(
            programme=programme,
            is_active=True
        ).count()

        if used_seats >= allocated_seats:
            raise StudentValidationError(
                f'Programme {programme.name} has reached maximum capacity ({allocated_seats} seats allocated, {used_seats} already enrolled)'
            )

        return True, used_seats, allocated_seats

    @staticmethod
    def check_existing_enrollment(user):
        """
        Check if user already has an active enrollment

        Args:
            user: User instance

        Returns:
            UniversityProgrammesEnrolment or None

        Raises:
            StudentValidationError: If user already enrolled
        """
        existing_enrollment = UniversityProgrammesEnrolment.objects.filter(
            user=user,
            is_active=True
        ).select_related('programme', 'programme_year', 'programme_section').first()

        if existing_enrollment:
            error_msg = (
                f'Student is already enrolled in '
                f'{existing_enrollment.programme.name} - '
                f'{existing_enrollment.programme_year.number_of_year}'
            )
            if existing_enrollment.programme_section:
                error_msg += f' - {existing_enrollment.programme_section.name}'
            raise StudentValidationError(error_msg)

        return None

    @staticmethod
    def get_or_create_user(email, first_name, last_name):
        """
        Get existing user by email or create new user

        Args:
            email: Email address
            first_name: First name
            last_name: Last name

        Returns:
            tuple: (User instance, bool) - (user, was_created)
        """
        # Check if user exists
        user = User.objects.filter(email=email).first()

        if user:
            # User exists - update profile name
            profile = UserProfile.objects.filter(user=user).first()
            if profile:
                profile.name = f"{first_name} {last_name}"
                profile.save()
            return user, False

        # User doesn't exist - create new user
        # Generate username from email (handle collisions)
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Create User with default password
        user = User.objects.create_user(
            username=username,
            email=email,
            password='Ebc@1234',  # Default password for all new students
            first_name=first_name,
            last_name=last_name
        )

        # Create Registration (this auto-creates UserProfile)
        reg = Registration()
        reg.register(user)

        # Get and update UserProfile
        profile = UserProfile.objects.get(user=user)
        profile.name = f"{first_name} {last_name}"
        profile.save()

        return user, True

    @staticmethod
    def get_or_create_user_metadata(user):
        """
        Get existing UserMetaData or create with defaults

        Args:
            user: User instance

        Returns:
            UserMetaData instance
        """
        metadata = UserMetaData.objects.filter(user=user).first()

        if not metadata:
            # Create with default values
            metadata = UserMetaData.objects.create(
                user=user,
                status='active',
                studio=True,
                careers_app=True
            )

        return metadata

    @staticmethod
    def ensure_college_student_link(user, college):
        """
        Ensure CollegeStudent link exists

        Args:
            user: User instance
            college: College instance

        Returns:
            CollegeStudent instance
        """
        college_student, created = CollegeStudent.objects.get_or_create(
            user=user,
            defaults={'college': college}
        )
        return college_student

    @staticmethod
    def create_enrollment(user, programme, programme_year, programme_section):
        """
        Create programme enrollment

        Args:
            user: User instance
            programme: UniversityProgrammes instance
            programme_year: UniversityProgrammesYear instance
            programme_section: UniversityProgrammesYearSection instance or None

        Returns:
            UniversityProgrammesEnrolment instance
        """
        enrolment = UniversityProgrammesEnrolment.objects.create(
            user=user,
            programme=programme,
            programme_year=programme_year,
            programme_section=programme_section,
            is_active=True
        )
        return enrolment

    @classmethod
    def create_student(cls, college, first_name, last_name, email, programme_id, year_name, section_name=''):
        """
        Complete student creation workflow
        Validates all inputs and creates all necessary records

        Args:
            college: College instance
            first_name: Student first name
            last_name: Student last name
            email: Student email
            programme_id: Programme ID
            year_name: Year name
            section_name: Section name (optional)

        Returns:
            dict: {'user_id': int, 'was_created': bool, 'message': str}

        Raises:
            StudentValidationError: If any validation fails
        """
        # Validate inputs
        first_name = first_name.strip()
        last_name = last_name.strip()
        email = email.strip().lower()
        year_name = year_name.strip()
        section_name = section_name.strip() if section_name else ''

        if not all([first_name, last_name, email, programme_id, year_name]):
            raise StudentValidationError(
                'First name, last name, email, programme, and year are required'
            )

        # Validate email format
        cls.validate_email_format(email)

        # Validate programme belongs to college
        programme = cls.validate_programme(programme_id, college)

        # Validate year
        programme_year = cls.validate_programme_year(programme, year_name)

        # Validate section (if provided)
        programme_section = cls.validate_programme_section(programme_year, section_name)

        # Check seat availability
        cls.check_seat_availability(programme)

        # Create all records in transaction
        with transaction.atomic():
            # Get or create user
            user, was_created = cls.get_or_create_user(email, first_name, last_name)

            # Get or create user metadata
            cls.get_or_create_user_metadata(user)

            # Ensure college student link
            cls.ensure_college_student_link(user, college)

            # Check for existing enrollment
            cls.check_existing_enrollment(user)

            # Create enrollment
            cls.create_enrollment(user, programme, programme_year, programme_section)

        return {
            'user_id': user.id,
            'was_created': was_created,
            'message': f'Student invitation sent to {email}'
        }
