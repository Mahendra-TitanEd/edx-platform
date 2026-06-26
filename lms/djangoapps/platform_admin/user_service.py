"""
Shared User Service Module
Reusable business logic for user creation and management
Used by Student, Faculty, and Institution Admin modules
"""

import logging
from django.db import transaction
from django.contrib.auth.models import User, Group
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from common.djangoapps.student.models import Registration, UserProfile
from lms.djangoapps.user_metadata.models import UserMetaData

logger = logging.getLogger(__name__)

# Default password for all new users (Student, Faculty, Institution Admin)
DEFAULT_PASSWORD = 'Ebc@1234'


class UserValidationError(Exception):
    """Custom exception for user validation errors"""
    pass


class UserService:
    """
    Shared service class for user management operations
    Provides reusable methods for creating users and metadata
    """

    @staticmethod
    def validate_email_format(email):
        """
        Validate email format

        Args:
            email: Email address string

        Raises:
            UserValidationError: If email format is invalid
        """
        try:
            validate_email(email)
        except ValidationError:
            raise UserValidationError('Invalid email format')

    @staticmethod
    def get_or_create_user(email, first_name, last_name, update_name=True):
        """
        Get existing user by email or create new user

        Args:
            email: Email address
            first_name: First name
            last_name: Last name
            update_name: Whether to update name if user exists (default True)

        Returns:
            tuple: (User instance, bool) - (user, was_created)
        """
        # Check if user exists
        user = User.objects.filter(email=email).first()

        if user:
            # User exists - optionally update name
            if update_name:
                user.first_name = first_name
                user.last_name = last_name
                user.save()

                # Update profile name
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
            password=DEFAULT_PASSWORD,  # Default password: Ebc@1234
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
    def get_or_create_user_metadata(user, status='active', studio=True, careers_app=True):
        """
        Get existing UserMetaData or create with defaults

        Args:
            user: User instance
            status: User status (default 'active')
            studio: Studio access (default True)
            careers_app: Careers app access (default True)

        Returns:
            tuple: (UserMetaData instance, bool) - (metadata, was_created)
        """
        metadata = UserMetaData.objects.filter(user=user).first()

        if metadata:
            # Metadata exists - return it without modification
            return metadata, False

        # Create with specified defaults
        metadata = UserMetaData.objects.create(
            user=user,
            status=status,
            studio=studio,
            careers_app=careers_app
        )

        return metadata, True

    @staticmethod
    def assign_to_group(user, group_name):
        """
        Assign user to a group (creates group if it doesn't exist)

        Args:
            user: User instance
            group_name: Name of the group

        Returns:
            Group instance
        """
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            # Create group if it doesn't exist
            group = Group.objects.create(name=group_name)
            logger.warning(f'{group_name} group did not exist, created new one')

        user.groups.add(group)
        return group

    @staticmethod
    def validate_required_fields(field_dict):
        """
        Validate that required fields are not empty

        Args:
            field_dict: Dictionary of field_name -> value

        Raises:
            UserValidationError: If any required field is missing
        """
        missing = [name for name, value in field_dict.items() if not value or not str(value).strip()]
        if missing:
            raise UserValidationError(f"Required fields missing: {', '.join(missing)}")
