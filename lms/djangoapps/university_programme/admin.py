"""
University Programme Admin Configuration
"""
from django.contrib import admin
from .models import (
    UniversityProgrammes,
    UniversityProgrammesYear,
    UniversityProgrammesYearSection,
    UniversityProgrammesEnrolment,
    UniversityBatch,
    UniversityGroup
)


class UniversityProgrammesYearInline(admin.TabularInline):
    """Inline admin for programme years"""
    model = UniversityProgrammesYear
    extra = 1
    fields = ('number_of_year',)


class UniversityProgrammesYearSectionInline(admin.TabularInline):
    """Inline admin for year sections"""
    model = UniversityProgrammesYearSection
    extra = 1
    fields = ('name',)


@admin.register(UniversityProgrammes)
class UniversityProgrammesAdmin(admin.ModelAdmin):
    """Admin for University Programmes"""
    list_display = (
        'short_name',
        'name',
        'university',
        'duration',
        'status',
        'allocated_seats',
        'enable_mystudio',
        'enable_careers_app',
        'created',
    )
    list_filter = ('status', 'duration', 'enable_mystudio', 'enable_careers_app', 'university')
    search_fields = ('short_name', 'name', 'description', 'university__name')
    readonly_fields = ('created', 'modified')
    inlines = [UniversityProgrammesYearInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('short_name', 'name', 'description', 'university')
        }),
        ('Configuration', {
            'fields': ('duration', 'status', 'color', 'allocated_seats')
        }),
        ('Apps', {
            'fields': ('enable_mystudio', 'enable_careers_app')
        }),
        ('Timestamps', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UniversityProgrammesYear)
class UniversityProgrammesYearAdmin(admin.ModelAdmin):
    """Admin for Programme Years"""
    list_display = ('number_of_year', 'programme', 'created')
    list_filter = ('programme',)
    search_fields = ('number_of_year', 'programme__name', 'programme__short_name')
    readonly_fields = ('created', 'modified')
    inlines = [UniversityProgrammesYearSectionInline]


@admin.register(UniversityProgrammesYearSection)
class UniversityProgrammesYearSectionAdmin(admin.ModelAdmin):
    """Admin for Year Sections"""
    list_display = ('name', 'programme_year', 'get_programme', 'created')
    list_filter = ('programme_year__programme',)
    search_fields = ('name', 'programme_year__number_of_year', 'programme_year__programme__name')
    readonly_fields = ('created', 'modified')

    def get_programme(self, obj):
        return obj.programme_year.programme
    get_programme.short_description = 'Programme'
    get_programme.admin_order_field = 'programme_year__programme'


@admin.register(UniversityProgrammesEnrolment)
class UniversityProgrammesEnrolmentAdmin(admin.ModelAdmin):
    """Admin for Programme Enrolments"""
    list_display = (
        'user',
        'programme',
        'programme_year',
        'programme_section',
        'is_active',
        'created'
    )
    list_filter = ('is_active', 'programme', 'programme_year')
    search_fields = (
        'user__username',
        'user__email',
        'programme__name',
        'programme__short_name'
    )
    readonly_fields = ('created', 'modified')
    raw_id_fields = ('user',)


@admin.register(UniversityBatch)
class UniversityBatchAdmin(admin.ModelAdmin):
    """Admin for University Batches"""
    list_display = ('name', 'university', 'created')
    list_filter = ('university',)
    search_fields = ('name', 'university__name')
    readonly_fields = ('created', 'modified')


@admin.register(UniversityGroup)
class UniversityGroupAdmin(admin.ModelAdmin):
    """Admin for University Groups"""
    list_display = (
        'name',
        'group_type',
        'programme',
        'university',
        'admin',
        'created'
    )
    list_filter = ('group_type', 'university', 'programme')
    search_fields = ('name', 'description', 'admin', 'programme__name', 'university__name')
    readonly_fields = ('created', 'modified')
    filter_horizontal = ('students',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'group_type', 'university', 'programme')
        }),
        ('Details', {
            'fields': ('admin', 'description', 'colour')
        }),
        ('Students', {
            'fields': ('students',)
        }),
        ('Timestamps', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )
