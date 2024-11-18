define(['js/views/validation', 'codemirror', 'underscore', 'jquery', 'jquery.ui', 'js/utils/date_utils',
    'js/models/uploads', 'js/views/uploads', 'js/views/license', 'js/models/license',
    'common/js/components/views/feedback_notification', 'jquery.timepicker', 'date', 'gettext',
    'js/views/learning_info', 'js/views/instructor_info', 'js/views/quote_info', 'js/views/review_info', 'edx-ui-toolkit/js/utils/string-utils'],
       function(ValidatingView, CodeMirror, _, $, ui, DateUtils, FileUploadModel,
                FileUploadDialog, LicenseView, LicenseModel, NotificationView,
                timepicker, date, gettext, LearningInfoView, InstructorInfoView, QuoteInfoView, ReviewInfoView, StringUtils) {
           var DetailsView = ValidatingView.extend({
    // Model class is CMS.Models.Settings.CourseDetails
               events: {
                   'input input': 'updateModel',
                   'input textarea': 'updateModel',
        // Leaving change in as fallback for older browsers
                   'change input': 'updateModel',
                   'change textarea': 'updateModel',
                   'change select': 'updateModel',
                   'click .remove-course-introduction-video': 'removeVideo',
                   'focus #course-overview': 'codeMirrorize',
                   'focus #course-about-sidebar-html': 'codeMirrorize',
                   'focus #overview_2': 'codeMirrorize',
                   'focus #introduction_video': 'codeMirrorize',
                   'focus #certificate_overview': 'codeMirrorize',
                   'focus #additional_campaign_info': 'codeMirrorize',
                   'mouseover .timezone': 'updateTime',
        // would love to move to a general superclass, but event hashes don't inherit in backbone :-(
                   'focus :input': 'inputFocus',
                   'blur :input': 'inputUnfocus',
                   'click .action-upload-image': 'uploadImage',
                   'click .add-course-learning-info': 'addLearningFields',
                   'click .add-course-instructor-info': 'addInstructorFields',
                   'click .add-course-quote-info': 'addQuoteFields',
                   'click .add-course-review-info': 'addReviewFields',
                   'change select#course_tags': 'addCourseTags',
                   'change select#course_categories': 'addCourseCategories',
               },

               initialize: function(options) {
                   options = options || {};
        // fill in fields
                   this.$el.find('#course-language').val(this.model.get('language'));
                   // Added by Mahendra
                   this.$el.find('#course_topic').val(this.model.get('course_topic'));
                   this.$el.find('#course_subject').val(this.model.get('course_subject'));
                   this.$el.find('#course_level').val(this.model.get('course_level'));
                   this.$el.find('#course_slug').val(this.model.get('course_slug'));
                   this.$el.find('#access_duration').val(this.model.get('access_duration'));
                   this.$el.find('#overview_2').val(this.model.get('overview_2'));
                   this.$el.find('#course_tags').val(this.safeJSONParse(this.model.get('course_tags'))).trigger("chosen:updated");
                   this.$el.find('#course_categories').val(this.safeJSONParse(this.model.get('course_categories'))).trigger("chosen:updated");
                   this.$el.find('#introduction_video').val(this.model.get('introduction_video'));
                   this.$el.find('#certificate_overview').val(this.model.get('certificate_overview'));
                   this.$el.find('#course-organization').val(this.model.get('org'));
                   this.$el.find('#course-number').val(this.model.get('course_id'));
                   this.$el.find('#course-name').val(this.model.get('run'));
                   this.$el.find('.set-date').datepicker({ dateFormat: 'm/d/yy' });
                   this.$el.find("#certificates-display-behavior").val(this.model.get("certificates_display_behavior"));
                   this.$el.find('#program_only_purchase_notes').val(this.model.get('program_only_purchase_notes'));
                   this.$el.find('#additional_campaign_info').val(this.model.get('additional_campaign_info'));
                   this.$el.find('#content_activation_window').val(this.model.get('content_activation_window'));
                   this.$el.find('#price_text').val(this.model.get('price_text'));
                   this.$el.find('#offer_text').val(this.model.get('offer_text'));
                   this.updateCertificatesDisplayBehavior();

        // Avoid showing broken image on mistyped/nonexistent image
                   this.$el.find('img').error(function() {
                       $(this).hide();
                   });
                   this.$el.find('img').load(function() {
                       $(this).show();
                   });

                   this.listenTo(this.model, 'invalid', this.handleValidationError);
                   this.listenTo(this.model, 'change', this.showNotificationBar);
                   this.selectorToField = _.invert(this.fieldToSelectorMap);
        // handle license separately, to avoid reimplementing view logic
                   this.licenseModel = new LicenseModel({asString: this.model.get('license')});
                   this.licenseView = new LicenseView({
                       model: this.licenseModel,
                       el: this.$('#course-license-selector').get(),
                       showPreview: true
                   });
                   this.listenTo(this.licenseModel, 'change', this.handleLicenseChange);

                   if (options.showMinGradeWarning || false) {
                       new NotificationView.Warning({
                           title: gettext('Course Credit Requirements'),
                           message: gettext('The minimum grade for course credit is not set.'),
                           closeIcon: true
                       }).show();
                   }

                   this.learning_info_view = new LearningInfoView({
                       el: $('.course-settings-learning-fields'),
                       model: this.model
                   });

                   this.instructor_info_view = new InstructorInfoView({
                       el: $('.course-instructor-details-fields'),
                       model: this.model
                   });

                   this.quote_info_view = new QuoteInfoView({
                       el: $('.course-quote-details-fields'),
                       model: this.model
                   });

                   this.review_info_view = new ReviewInfoView({
                       el: $('.course-review-details-fields'),
                       model: this.model
                   });
               },

               render: function() {
        // Clear any image preview timeouts set in this.updateImagePreview
                   clearTimeout(this.imageTimer);

                   DateUtils.setupDatePicker('start_date', this);
                   DateUtils.setupDatePicker('end_date', this);
                   DateUtils.setupDatePicker('certificate_available_date', this);
                   DateUtils.setupDatePicker('enrollment_start', this);
                   DateUtils.setupDatePicker('enrollment_end', this);
                   DateUtils.setupDatePicker('upgrade_deadline', this);
                   // Added by Mahendra
                   DateUtils.setupDatePicker('assignment_due_date', this);
                   this.$el.find('#' + this.fieldToSelectorMap.overview).val(this.model.get('overview'));
                   this.codeMirrorize(null, $('#course-overview')[0]);

                   if (this.model.get('title') !== '') {
                       this.$el.find('#' + this.fieldToSelectorMap.title).val(this.model.get('title'));
                   } else {
                       var displayName = this.$el.find('#' + this.fieldToSelectorMap.title).attr('data-display-name');
                       this.$el.find('#' + this.fieldToSelectorMap.title).val(displayName);
                   }
                   this.$el.find('#' + this.fieldToSelectorMap.subtitle).val(this.model.get('subtitle'));
                   this.$el.find('#' + this.fieldToSelectorMap.duration).val(this.model.get('duration'));
                   this.$el.find('#' + this.fieldToSelectorMap.description).val(this.model.get('description'));

                   this.$el.find('#' + this.fieldToSelectorMap.short_description).val(this.model.get('short_description'));
                   this.$el.find('#' + this.fieldToSelectorMap.about_sidebar_html).val(
                       this.model.get('about_sidebar_html')
                   );
                   this.codeMirrorize(null, $('#course-about-sidebar-html')[0]);

                   this.$el.find('.current-course-introduction-video iframe').attr('src', this.model.videosourceSample());
                   this.$el.find('#' + this.fieldToSelectorMap.intro_video).val(this.model.get('intro_video') || '');
                   if (this.model.has('intro_video')) {
                       this.$el.find('.remove-course-introduction-video').show();
                   } else this.$el.find('.remove-course-introduction-video').hide();

                   this.$el.find('#' + this.fieldToSelectorMap.effort).val(this.model.get('effort'));
                   this.$el.find("#" + this.fieldToSelectorMap.certificates_display_behavior).val(this.model.get('certificates_display_behavior'));
                   this.updateCertificatesDisplayBehavior();

                   var courseImageURL = this.model.get('course_image_asset_path');
                   this.$el.find('#course-image-url').val(courseImageURL);
                   this.$el.find('#course-image').attr('src', courseImageURL);

                   var bannerImageURL = this.model.get('banner_image_asset_path');
                   this.$el.find('#banner-image-url').val(bannerImageURL);
                   this.$el.find('#banner-image').attr('src', bannerImageURL);

                   var videoThumbnailImageURL = this.model.get('video_thumbnail_image_asset_path');
                   this.$el.find('#video-thumbnail-image-url').val(videoThumbnailImageURL);
                   this.$el.find('#video-thumbnail-image').attr('src', videoThumbnailImageURL);

                   var pre_requisite_courses = this.model.get('pre_requisite_courses');
                   pre_requisite_courses = pre_requisite_courses.length > 0 ? pre_requisite_courses : '';
                   this.$el.find('#' + this.fieldToSelectorMap.pre_requisite_courses).val(pre_requisite_courses);

                   if (this.model.get('entrance_exam_enabled') == 'true') {
                       this.$('#' + this.fieldToSelectorMap.entrance_exam_enabled).attr('checked', this.model.get('entrance_exam_enabled'));
                       this.$('.div-grade-requirements').show();
                   } else {
                       this.$('#' + this.fieldToSelectorMap.entrance_exam_enabled).removeAttr('checked');
                       this.$('.div-grade-requirements').hide();
                   }
                   this.$('#' + this.fieldToSelectorMap.entrance_exam_minimum_score_pct).val(this.model.get('entrance_exam_minimum_score_pct'));

                   var selfPacedButton = this.$('#course-pace-self-paced'),
                       instructorPacedButton = this.$('#course-pace-instructor-paced'),
                       paceToggleTip = this.$('#course-pace-toggle-tip');
                   (this.model.get('self_paced') ? selfPacedButton : instructorPacedButton).attr('checked', true);
                   if (this.model.canTogglePace()) {
                       selfPacedButton.removeAttr('disabled');
                       instructorPacedButton.removeAttr('disabled');
                       paceToggleTip.text('');
                   } else {
                       selfPacedButton.attr('disabled', true);
                       instructorPacedButton.attr('disabled', true);
                       paceToggleTip.text(gettext('Course pacing cannot be changed once a course has started.'));
                   }

                   this.licenseView.render();
                   this.learning_info_view.render();
                   this.instructor_info_view.render();
                   this.quote_info_view.render();
                   this.review_info_view.render();

                   // Added by Mahendra
                   this.$el.find('#' + this.fieldToSelectorMap['course_topic']).val(this.model.get('course_topic'));
                   this.$el.find('#' + this.fieldToSelectorMap['course_subject']).val(this.model.get('course_subject'));
                   this.$el.find('#' + this.fieldToSelectorMap['course_level']).val(this.model.get('course_level'));
                   this.$el.find('#' + this.fieldToSelectorMap['course_slug']).val(this.model.get('course_slug'));
                   this.$el.find('#' + this.fieldToSelectorMap['access_duration']).val(this.model.get('access_duration'));
                   this.$el.find('#' + this.fieldToSelectorMap.overview_2).val(this.model.get('overview_2'));
                   this.codeMirrorize(null, $('#overview_2')[0]);
                   this.$el.find('#' + this.fieldToSelectorMap['course_tags']).val(this.safeJSONParse(this.model.get('course_tags'))).trigger("chosen:updated");
                   this.$el.find('#' + this.fieldToSelectorMap['course_categories']).val(this.safeJSONParse(this.model.get('course_categories'))).trigger("chosen:updated");
                   this.$el.find('#' + this.fieldToSelectorMap.certificate_overview).val(this.model.get('certificate_overview'));
                   this.codeMirrorize(null, $('#certificate_overview')[0]);

                   this.$el.find('#' + this.fieldToSelectorMap.introduction_video).val(this.model.get('introduction_video'));
                   this.codeMirrorize(null, $('#introduction_video')[0]);
                   this.$el.find('#' + this.fieldToSelectorMap['program_only_purchase_notes']).val(this.model.get('program_only_purchase_notes'));
                   this.$el.find('#' + this.fieldToSelectorMap['additional_campaign_info']).val(this.model.get('additional_campaign_info'));
                   this.codeMirrorize(null, $('#additional_campaign_info')[0]);
                   this.$el.find('#' + this.fieldToSelectorMap['content_activation_window']).val(this.model.get('content_activation_window'));
                   this.$el.find('#' + this.fieldToSelectorMap['price_text']).val(this.model.get('price_text'));
                   this.$el.find('#' + this.fieldToSelectorMap['offer_text']).val(this.model.get('offer_text'));

                   if ((this.model.get('show_outline') == 'true')) {
                       this.$('#' + this.fieldToSelectorMap.show_outline).attr('checked','checked');
                   } else {
                       this.$('#' + this.fieldToSelectorMap.show_outline).removeAttr('checked');
                   }
                   if ((this.model.get('is_upcoming') == 'true')) {
                       this.$('#' + this.fieldToSelectorMap.is_upcoming).attr('checked','checked');
                   } else {
                       this.$('#' + this.fieldToSelectorMap.is_upcoming).removeAttr('checked');
                   }
                   if ((this.model.get('in_subscription') == 'true')) {
                       this.$('#' + this.fieldToSelectorMap.in_subscription).attr('checked','checked');
                   } else {
                       this.$('#' + this.fieldToSelectorMap.in_subscription).removeAttr('checked');
                   }
                   if ((this.model.get('is_talks') == 'true')) {
                       this.$('#' + this.fieldToSelectorMap.is_talks).attr('checked','checked');
                   } else {
                       this.$('#' + this.fieldToSelectorMap.is_talks).removeAttr('checked');
                   }
                   if ((this.model.get('program_only_purchase') == 'true')) {
                       this.$('#' + this.fieldToSelectorMap.program_only_purchase).attr('checked','checked');
                   } else {
                       this.$('#' + this.fieldToSelectorMap.program_only_purchase).removeAttr('checked');
                   }
                   if ((this.model.get('recently_updated') == 'true')) {
                       this.$('#' + this.fieldToSelectorMap.recently_updated).attr('checked','checked');
                   } else {
                       this.$('#' + this.fieldToSelectorMap.recently_updated).removeAttr('checked');
                   }
                   return this;
               },
               fieldToSelectorMap: {
                   language: 'course-language',
                   start_date: 'course-start',
                   end_date: 'course-end',
                   enrollment_start: 'enrollment-start',
                   enrollment_end: 'enrollment-end',
                   upgrade_deadline: 'upgrade-deadline',
                   certificate_available_date: 'certificate-available',
                   certificates_display_behavior: 'certificates-display-behavior',
                   overview: 'course-overview',
                   title: 'course-title',
                   subtitle: 'course-subtitle',
                   duration: 'course-duration',
                   description: 'course-description',
                   about_sidebar_html: 'course-about-sidebar-html',
                   short_description: 'course-short-description',
                   intro_video: 'course-introduction-video',
                   effort: 'course-effort',
                   course_image_asset_path: 'course-image-url',
                   banner_image_asset_path: 'banner-image-url',
                   video_thumbnail_image_asset_path: 'video-thumbnail-image-url',
                   pre_requisite_courses: 'pre-requisite-course',
                   entrance_exam_enabled: 'entrance-exam-enabled',
                   entrance_exam_minimum_score_pct: 'entrance-exam-minimum-score-pct',
                   course_settings_learning_fields: 'course-settings-learning-fields',
                   add_course_learning_info: 'add-course-learning-info',
                   add_course_instructor_info: 'add-course-instructor-info',
                   course_learning_info: 'course-learning-info',
                   course_topic: 'course_topic',    // Added by Mahendra
                   course_subject: 'course_subject', // Added by Mahendra
                   course_level: 'course_level', // Added by Mahendra
                   course_slug: 'course_slug', // Added by Mahendra
                   access_duration: 'access_duration', // Added by Mahendra
                   overview_2: 'overview_2', // Added by Mahendra
                   introduction_video: 'introduction_video', // Added by Mahendra
                   certificate_overview: 'certificate_overview', // Added by Mahendra
                   add_course_quote_info: 'add-course-quote-info', // Added by Mahendra
                   add_course_review_info: 'add-course-review-info', // Added by Mahendra
                   assignment_due_date: 'assignment-due', // Added by Mahendra
                   show_outline: 'show-outline', // Added by Mahendra
                   is_upcoming: 'is-upcoming', // Added by Mahendra
                   in_subscription: 'in-subscription', // Added by Mahendra
                   is_talks: 'is-talks', // Added by Mahendra
                   course_tags: 'course_tags',    // Added by Mahendra
                   course_categories: 'course_categories',    // Added by Mahendra
                   program_only_purchase: 'program-only-purchase',    // Added by Mahendra
                   program_only_purchase_notes: 'program_only_purchase_notes',    // Added by Mahendra
                   price_text: 'price_text',    // Added by Mahendra
                   offer_text: 'offer_text',    // Added by Mahendra
                   recently_updated: 'recently-updated', // Added by Mahendra
                   additional_campaign_info: 'additional_campaign_info',    // Added by Mahendra
                   content_activation_window: 'content_activation_window', // Added by Mahendra
               },

               addLearningFields: function() {
        /*
        * Add new course learning fields.
        * */
                   var existingInfo = _.clone(this.model.get('learning_info'));
                   existingInfo.push('');
                   this.model.set('learning_info', existingInfo);
               },

               addInstructorFields: function() {
        /*
        * Add new course instructor fields.
        * */
                   var instructors = this.model.get('instructor_info').instructors.slice(0);
                   instructors.push({
                       name: '',
                       title: '',
                       organization: '',
                       image: '',
                       bio: ''
                   });
                   this.model.set('instructor_info', {instructors: instructors});
               },

               addCourseTags: function() {
                   var topics = $("#course_tags").val();
                   this.model.set('course_tags', JSON.stringify(topics));
               },

               addCourseCategories: function() {
                   var topics = $("#course_categories").val();
                   this.model.set('course_categories', JSON.stringify(topics));
               },

               addQuoteFields: function() {
        /*
        * Add new course Quote fields.
        * */
                   var quotes = this.model.get('quote_info').quotes.slice(0);
                   quotes.push({
                       name: '',
                       sequence: '',
                       image: '',
                       bio: ''
                   });
                   this.model.set('quote_info', {quotes: quotes});
               },

               addReviewFields: function() {
                /*
                * Add new course Review fields.
                * */
                   var reviews = this.model.get('review_info').reviews.slice(0);
                   reviews.push({
                       name: '',
                       sequence: '',
                       image: '',
                       bio: ''
                   });
                   this.model.set('review_info', {reviews: reviews});
               },

               updateTime: function(e) {
                   var now = new Date(),
                       hours = now.getUTCHours(),
                       minutes = now.getUTCMinutes(),
                       currentTimeText = StringUtils.interpolate(
                gettext('{hours}:{minutes} (current UTC time)'),
                           {
                               hours: hours,
                               minutes: minutes
                           }
            );

                   $(e.currentTarget).attr('title', currentTimeText);
               },
               updateModel: function(event) {
                   var value;
                   var index = event.currentTarget.getAttribute('data-index');
                   switch (event.currentTarget.id) {
                   case 'course-learning-info-' + index:
                       value = $(event.currentTarget).val();
                       var learningInfo = this.model.get('learning_info');
                       learningInfo[index] = value;
                       this.showNotificationBar();
                       break;
                   case 'course-instructor-name-' + index:
                   case 'course-instructor-title-' + index:
                   case 'course-instructor-organization-' + index:
                   case 'course-instructor-bio-' + index:
                       value = $(event.currentTarget).val();
                       var field = event.currentTarget.getAttribute('data-field'),
                           instructors = this.model.get('instructor_info').instructors.slice(0);
                       instructors[index][field] = value;
                       this.model.set('instructor_info', {instructors: instructors});
                       this.showNotificationBar();
                       break;
                   case 'course-instructor-image-' + index:
                       instructors = this.model.get('instructor_info').instructors.slice(0);
                       instructors[index].image = $(event.currentTarget).val();
                       this.model.set('instructor_info', {instructors: instructors});
                       this.showNotificationBar();
                       this.updateImagePreview(event.currentTarget, '#course-instructor-image-preview-' + index);
                       break;
                   // Added by Mahendra
                   case 'course-quote-name-' + index:
                   case 'course-quote-sequence-' + index:
                   case 'course-quote-bio-' + index:
                       value = $(event.currentTarget).val();
                       var field = event.currentTarget.getAttribute('data-field'),
                           quotes = this.model.get('quote_info').quotes.slice(0);
                       quotes[index][field] = value;
                       this.model.set('quote_info', {quotes: quotes});
                       this.showNotificationBar();
                       break;
                   case 'course-quote-image-' + index:
                       quotes = this.model.get('quote_info').quotes.slice(0);
                       quotes[index].image = $(event.currentTarget).val();
                       this.model.set('quote_info', {quotes: quotes});
                       this.showNotificationBar();
                       this.updateImagePreview(event.currentTarget, '#course-quote-image-preview-' + index);
                       break;
                   case 'course-review-name-' + index:
                   case 'course-review-sequence-' + index:
                   case 'course-review-bio-' + index:
                       value = $(event.currentTarget).val();
                       var field = event.currentTarget.getAttribute('data-field'),
                           reviews = this.model.get('review_info').reviews.slice(0);
                       reviews[index][field] = value;
                       this.model.set('review_info', {reviews: reviews});
                       this.showNotificationBar();
                       break;
                   case 'course-review-image-' + index:
                       reviews = this.model.get('review_info').reviews.slice(0);
                       reviews[index].image = $(event.currentTarget).val();
                       this.model.set('review_info', {reviews: reviews});
                       this.showNotificationBar();
                       this.updateImagePreview(event.currentTarget, '#course-review-image-preview-' + index);
                       break;
                   case 'course-image-url':
                       this.updateImageField(event, 'course_image_name', '#course-image');
                       break;
                   case 'banner-image-url':
                       this.updateImageField(event, 'banner_image_name', '#banner-image');
                       break;
                   case 'video-thumbnail-image-url':
                       this.updateImageField(event, 'video_thumbnail_image_name', '#video-thumbnail-image');
                       break;
                   case 'entrance-exam-enabled':
                       if ($(event.currentTarget).is(':checked')) {
                           this.$('.div-grade-requirements').show();
                       } else {
                           this.$('.div-grade-requirements').hide();
                       }
                       this.setField(event);
                       break;
                   case 'show-outline':
                       if ($(event.currentTarget).is(':checked')) {
                           this.model.set('show_outline', 'true');
                       } else {
                           this.model.set('show_outline', 'false');
                       }
                       this.setField(event);
                       break;
                   case 'is-upcoming':
                       if ($(event.currentTarget).is(':checked')) {
                           this.model.set('is_upcoming', 'true');
                       } else {
                           this.model.set('is_upcoming', 'false');
                       }
                       this.setField(event);
                       break;
                   case 'in-subscription':
                       if ($(event.currentTarget).is(':checked')) {
                           this.model.set('in_subscription', 'true');
                       } else {
                           this.model.set('in_subscription', 'false');
                       }
                       this.setField(event);
                       break;
                   case 'is-talks':
                       if ($(event.currentTarget).is(':checked')) {
                           this.model.set('is_talks', 'true');
                       } else {
                           this.model.set('is_talks', 'false');
                       }
                       this.setField(event);
                       break;
                   case 'program-only-purchase':
                       if ($(event.currentTarget).is(':checked')) {
                           this.model.set('program_only_purchase', 'true');
                       } else {
                           this.model.set('program_only_purchase', 'false');
                       }
                       this.setField(event);
                       break;
                   case 'recently-updated':
                       if ($(event.currentTarget).is(':checked')) {
                           this.model.set('recently_updated', 'true');
                       } else {
                           this.model.set('recently_updated', 'false');
                       }
                       this.setField(event);
                       break;
                   case 'entrance-exam-minimum-score-pct':
            // If the val is an empty string then update model with default value.
                       if ($(event.currentTarget).val() === '') {
                           this.model.set('entrance_exam_minimum_score_pct', this.model.defaults.entrance_exam_minimum_score_pct);
                       } else {
                           this.setField(event);
                       }
                       break;
                   case 'pre-requisite-course':
                       var value = $(event.currentTarget).val();
                       value = value == '' ? [] : [value];
                       this.model.set('pre_requisite_courses', value);
                       break;
        // Don't make the user reload the page to check the Youtube ID.
        // Wait for a second to load the video, avoiding egregious AJAX calls.
                   case 'course-introduction-video':
                       this.clearValidationErrors();
                       var previewsource = this.model.set_videosource($(event.currentTarget).val());
                       clearTimeout(this.videoTimer);
                       this.videoTimer = setTimeout(_.bind(function() {
                           this.$el.find('.current-course-introduction-video iframe').attr('src', previewsource);
                           if (this.model.has('intro_video')) {
                               this.$el.find('.remove-course-introduction-video').show();
                           } else {
                               this.$el.find('.remove-course-introduction-video').hide();
                           }
                       }, this), 1000);
                       break;
                   case 'course-pace-self-paced':
            // Fallthrough to handle both radio buttons
                   case 'course-pace-instructor-paced':
                       this.model.set('self_paced', JSON.parse(event.currentTarget.value));
                       break;
                   case 'certificates-display-behavior':
                       this.setField(event);
                       this.updateCertificatesDisplayBehavior();
                       break;
                   case 'course-language':
                   case 'course-effort':
                   case 'course-title':
                   case 'course-subtitle':
                   case 'course-duration':
                   case 'course-description':
                    // Added by Mahendra
                   case 'course_topic':
                   case 'course_subject':
                   case 'course_level':
                   case 'course_slug':
                   case 'access_duration':
                   case 'overview_2':
                   case 'course_tags':
                   case 'course_categories':
                   case 'introduction_video':
                   case 'certificate_overview':
                   case 'program_only_purchase_notes':
                   case 'additional_campaign_info':
                   case 'content_activation_window':
                   case 'price_text':
                   case 'offer_text':
                   case 'course-short-description':
                       this.setField(event);
                       break;
                   default: // Everything else is handled by datepickers and CodeMirror.
                       break;
                   }
               },
               updateImageField: function(event, image_field, selector) {
                   this.setField(event);
                   var url = $(event.currentTarget).val();
                   var image_name = _.last(url.split('/'));
        // If image path is entered directly, we need to strip the asset prefix
                   image_name = _.last(image_name.split('block@'));
                   this.model.set(image_field, image_name);
                   this.updateImagePreview(event.currentTarget, selector);
               },
               updateImagePreview: function(imagePathInputElement, previewSelector) {
        // Wait to set the image src until the user stops typing
                   clearTimeout(this.imageTimer);
                   this.imageTimer = setTimeout(function() {
                       $(previewSelector).attr('src', $(imagePathInputElement).val());
                   }, 1000);
               },
               removeVideo: function(event) {
                   event.preventDefault();
                   if (this.model.has('intro_video')) {
                       this.model.set_videosource(null);
                       this.$el.find('.current-course-introduction-video iframe').attr('src', '');
                       this.$el.find('#' + this.fieldToSelectorMap.intro_video).val('');
                       this.$el.find('.remove-course-introduction-video').hide();
                   }
               },
               codeMirrors: {},
               codeMirrorize: function(e, forcedTarget) {
                   var thisTarget, cachethis, field, cmTextArea;
                   if (forcedTarget) {
                       thisTarget = forcedTarget;
                       thisTarget.id = $(thisTarget).attr('id');
                   } else if (e !== null) {
                       thisTarget = e.currentTarget;
                   } else {
            // e and forcedTarget can be null so don't deference it
            // This is because in cases where we have a marketing site
            // we don't display the codeMirrors for editing the marketing
            // materials, except we do need to show the 'set course image'
            // workflow. So in this case e = forcedTarget = null.
                       return;
                   }

                   if (!this.codeMirrors[thisTarget.id]) {
                       cachethis = this;
                       field = this.selectorToField[thisTarget.id];
                       this.codeMirrors[thisTarget.id] = CodeMirror.fromTextArea(thisTarget, {
                           mode: 'text/html', lineNumbers: true, lineWrapping: true});
                       this.codeMirrors[thisTarget.id].on('change', function(mirror) {
                           mirror.save();
                           cachethis.clearValidationErrors();
                           var newVal = mirror.getValue();
                           if (cachethis.model.get(field) != newVal) {
                               cachethis.setAndValidate(field, newVal);
                           }
                       });
                       cmTextArea = this.codeMirrors[thisTarget.id].getInputField();
                       cmTextArea.setAttribute('id', thisTarget.id + '-cm-textarea');
                   }
               },

                updateCertificatesDisplayBehavior: function() {
                    /*
                    Hides and clears the certificate available date field if a display behavior that doesn't use it is
                    chosen. Because we are clearing it, toggling back to "end_with_date" will require re-entering the date
                    */
                    if (!this.useV2CertDisplaySettings){
                        return;
                    }
                    let showDatepicker = this.model.get("certificates_display_behavior") == "end_with_date";
                    let datepicker = this.$el.find('#certificate-available-date');
                    let certificateAvailableDateField = this.$el.find('#field-certificate-available-date');

                    if (showDatepicker) {
                        datepicker.prop('disabled', false);
                        certificateAvailableDateField.removeClass("hidden");
                    } else {
                        datepicker.prop('disabled', true);
                        datepicker.val(null);
                        this.clearValidationErrors();
                        this.setAndValidate("certificate_available_date", null)
                        certificateAvailableDateField.addClass("hidden");
                    }
                },
               revertView: function() {
        // Make sure that the CodeMirror instance has the correct
        // data from its corresponding textarea
                   var self = this;
                   this.model.fetch({
                       success: function() {
                           self.render();
                           _.each(self.codeMirrors, function(mirror) {
                               var ele = mirror.getTextArea();
                               var field = self.selectorToField[ele.id];
                               mirror.setValue(self.model.get(field));
                           });
                           self.licenseModel.setFromString(self.model.get('license'), {silent: true});
                           self.licenseView.render();
                       },
                       reset: true,
                       silent: true});
               },
               setAndValidate: function(attr, value) {
        // If we call model.set() with {validate: true}, model fields
        // will not be set if validation fails. This puts the UI and
        // the model in an inconsistent state, and causes us to not
        // see the right validation errors the next time validate() is
        // called on the model. So we set *without* validating, then
        // call validate ourselves.
                   this.model.set(attr, value);
                   this.model.isValid();
               },

               showNotificationBar: function() {
        // We always call showNotificationBar with the same args, just
        // delegate to superclass
                   ValidatingView.prototype.showNotificationBar.call(this,
                                                          this.save_message,
                                                          _.bind(this.saveView, this),
                                                          _.bind(this.revertView, this));
               },

                // Added by Mahendra
                safeJSONParse: function(value) {
                    try {
                        return JSON.parse(value);
                    } catch (e) {
                        return [];
                    }
                },

               uploadImage: function(event) {
                   event.preventDefault();
                   var title = '',
                       selector = '',
                       image_key = '',
                       image_path_key = '';
                   switch (event.currentTarget.id) {
                   case 'upload-course-image':
                       title = gettext('Upload your course image.');
                       selector = '#course-image';
                       image_key = 'course_image_name';
                       image_path_key = 'course_image_asset_path';
                       break;
                   case 'upload-banner-image':
                       title = gettext('Upload your banner image.');
                       selector = '#banner-image';
                       image_key = 'banner_image_name';
                       image_path_key = 'banner_image_asset_path';
                       break;
                   case 'upload-video-thumbnail-image':
                       title = gettext('Upload your video thumbnail image.');
                       selector = '#video-thumbnail-image';
                       image_key = 'video_thumbnail_image_name';
                       image_path_key = 'video_thumbnail_image_asset_path';
                       break;
                   }

                   var upload = new FileUploadModel({
                       title: title,
                       message: gettext('Files must be in JPEG or PNG format.'),
                       mimeTypes: ['image/jpeg', 'image/png']
                   });
                   var self = this;
                   var modal = new FileUploadDialog({
                       model: upload,
                       onSuccess: function(response) {
                           var options = {};
                           options[image_key] = response.asset.display_name;
                           options[image_path_key] = response.asset.url;
                           self.model.set(options);
                           self.render();
                           $(selector).attr('src', self.model.get(image_path_key));
                       }
                   });
                   modal.show();
               },

               handleLicenseChange: function() {
                   this.showNotificationBar();
                   this.model.set('license', this.licenseModel.toString());
               }
           });

           return DetailsView;
       }); // end define()
