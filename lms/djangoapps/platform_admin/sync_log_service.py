"""
Helpers for Platform Admin Sync Log events.
"""

import logging
from datetime import timedelta

from django.db.models import Prefetch, Q
from django.utils import timezone

from college.models import CollegeStudent
from lms.djangoapps.platform_admin.models import SyncLogEvent
from lms.djangoapps.university_programme.models import UniversityProgrammesEnrolment

logger = logging.getLogger(__name__)


def record_sync_event(
    *,
    college,
    student_name,
    student_email,
    auth_method='Direct',
    programme_name='',
    year_name='',
    section_name='',
    account_status='created',
    result='granted',
    block_reason='',
    user=None,
    event_at=None,
):
    """Create a sync log event (fail-soft)."""
    try:
        return SyncLogEvent.objects.create(
            college=college,
            user=user,
            student_name=(student_name or '').strip() or (student_email or 'Unknown'),
            student_email=(student_email or '').strip() or 'unknown@example.com',
            auth_method=auth_method or 'Direct',
            programme_name=programme_name or '',
            year_name=year_name or '',
            section_name=section_name or '',
            account_status=account_status or 'created',
            result=result or 'granted',
            block_reason=block_reason or '',
            event_at=event_at or timezone.now(),
        )
    except Exception as exc:
        logger.warning('record_sync_event failed: %s', exc, exc_info=True)
        return None


def seed_sync_log_from_students(college):
    """
    If this college has no sync events yet, seed from existing student enrolments
    so the Sync Log page is useful immediately.
    """
    if SyncLogEvent.objects.filter(college=college).exists():
        return 0

    created = 0
    students = CollegeStudent.objects.filter(college=college).select_related(
        'user', 'user__profile'
    ).prefetch_related(
        Prefetch(
            'user__programme_enrolments',
            queryset=UniversityProgrammesEnrolment.objects.select_related(
                'programme', 'programme_year', 'programme_section'
            ).filter(is_active=True)
        )
    ).order_by('-user__date_joined')[:500]

    now = timezone.now()
    students = list(students)

    for idx, cs in enumerate(students):
        user = cs.user
        enrolment = user.programme_enrolments.first() if hasattr(user, 'programme_enrolments') else None
        programme = enrolment.programme if enrolment else None
        year = enrolment.programme_year if enrolment else None
        section = enrolment.programme_section if enrolment else None
        name = user.get_full_name() or user.username
        # Spread seeded events across the last ~28 days so 30-day stats are populated
        event_at = now - timedelta(days=min(27, idx), hours=(idx % 11), minutes=(idx * 7) % 60)
        if user.date_joined and user.date_joined <= now:
            # Prefer real join time when it falls inside the window
            if user.date_joined >= now - timedelta(days=30):
                event_at = user.date_joined
        record_sync_event(
            college=college,
            user=user,
            student_name=name,
            student_email=user.email or '',
            auth_method='Direct',
            programme_name=(programme.short_name or programme.name) if programme else '',
            year_name=year.number_of_year if year else '',
            section_name=section.name if section else '',
            account_status='created',
            result='granted',
            event_at=event_at,
        )
        created += 1
    return created


def serialize_event(event):
    year_display = event.year_name or ''
    # Normalize "Year 3" -> keep as-is for attrs; template also accepts bare numbers
    return {
        'id': event.id,
        'ts': timezone.localtime(event.event_at).strftime('%d %b %Y, %H:%M'),
        'ts_iso': event.event_at.isoformat(),
        'name': event.student_name,
        'email': event.student_email,
        'auth': event.auth_method,
        'programme': event.programme_name or '—',
        'year': year_display or '—',
        'section': event.section_name or '',
        'account': event.account_status,
        'result': event.result,
        'blockReason': event.block_reason or '',
    }


def query_sync_events(college, *, result='all', auth='all', programme='all', search='', days=90):
    seed_sync_log_from_students(college)

    since = timezone.now() - timedelta(days=days)
    qs = SyncLogEvent.objects.filter(college=college, event_at__gte=since)

    if result in ('granted', 'blocked'):
        qs = qs.filter(result=result)
    if auth in ('SSO', 'Direct', 'Code'):
        qs = qs.filter(auth_method=auth)
    if programme and programme != 'all':
        qs = qs.filter(programme_name=programme)
    if search:
        qs = qs.filter(
            Q(student_name__icontains=search) | Q(student_email__icontains=search)
        )
    return qs


def sync_log_stats(college, days=30):
    since = timezone.now() - timedelta(days=days)
    qs = SyncLogEvent.objects.filter(college=college, event_at__gte=since)
    total = qs.count()
    granted = qs.filter(result='granted').count()
    blocked = qs.filter(result='blocked').count()
    created = qs.filter(account_status='created').count()

    week_ago = timezone.now() - timedelta(days=7)
    blocked_week = SyncLogEvent.objects.filter(
        college=college, event_at__gte=week_ago, result='blocked'
    )
    blocked_week_count = blocked_week.count()
    blocked_programmes = list(
        blocked_week.exclude(programme_name='')
        .values_list('programme_name', flat=True)
        .distinct()[:3]
    )

    banner = {
        'ok': blocked_week_count == 0,
        'blocked_count': blocked_week_count,
        'programmes': blocked_programmes,
    }
    return {
        'total': total,
        'granted': granted,
        'blocked': blocked,
        'created': created,
        'banner': banner,
    }


def programme_filter_options(college):
    names = (
        SyncLogEvent.objects.filter(college=college)
        .exclude(programme_name='')
        .values_list('programme_name', flat=True)
        .distinct()
        .order_by('programme_name')
    )
    return list(names)
