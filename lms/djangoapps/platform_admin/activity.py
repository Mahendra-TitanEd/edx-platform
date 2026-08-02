"""
Thin Platform Admin wrapper around recent_activities.ActivityService.

Keeps api_views free of import boilerplate and standardises module tagging.
"""

import logging

from recent_activities.models import MODULE_PLATFORM
from recent_activities.services import ActivityService

logger = logging.getLogger(__name__)


def record_platform_activity(
    *,
    actor,
    college,
    description,
    activity_type='OTHER',
    metadata=None,
    dedupe_key='',
):
    """Record a Platform Admin activity (fail-soft)."""
    try:
        ActivityService.record_on_commit(
            user=actor,
            college=college,
            module=MODULE_PLATFORM,
            description=description,
            activity_type=activity_type,
            metadata=metadata or {},
            dedupe_key=dedupe_key or '',
        )
    except Exception as exc:
        logger.warning("record_platform_activity failed: %s", exc, exc_info=True)


def bold(text):
    return ActivityService.bold(text)
