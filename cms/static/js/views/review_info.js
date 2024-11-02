// Backbone Application View: Course Review Information

define([
    'jquery',
    'underscore',
    'backbone',
    'gettext',
    'js/utils/templates',
    'js/models/uploads',
    'js/views/uploads',
    'edx-ui-toolkit/js/utils/html-utils'
],
    function($, _, Backbone, gettext, TemplateUtils, FileUploadModel, FileUploadDialog, HtmlUtils) {
        'use strict';
        var ReviewInfoView = Backbone.View.extend({

            events: {
                'click .remove-review-data': 'removeReview',
                'click .action-upload-review-image': 'uploadReviewImage'
            },

            initialize: function() {
                // Set up the initial state of the attributes set for this model instance
                _.bindAll(this, 'render');
                this.template = this.loadTemplate('course-review-details');
                this.listenTo(this.model, 'change:review_info', this.render);
            },

            loadTemplate: function(name) {
                // Retrieve the corresponding template for this model
                return TemplateUtils.loadTemplate(name);
            },

            render: function() {
                var attributes;
                // Assemble the render view for this model.
                $('.course-review-details-fields').empty();
                var self = this;
                $.each(this.model.get('review_info').reviews, function(index, data) {
                    attributes = {
                        data: data,
                        index: index
                    };
                    $(self.el).append(HtmlUtils.HTML(self.template(attributes)).toString());
                });

                // Avoid showing broken image on mistyped/nonexistent image
                this.$el.find('img').error(function() {
                    $(this).hide();
                });
                this.$el.find('img').load(function() {
                    $(this).show();
                });
            },

            removeReview: function(event) {
                /*
                 * Remove course Course Review fields.
                 * */
                event.preventDefault();
                var index = event.currentTarget.getAttribute('data-index'),
                    reviews = this.model.get('review_info').reviews.slice(0);
                reviews.splice(index, 1);
                this.model.set('review_info', {reviews: reviews});
            },

            uploadReviewImage: function(event) {
                /*
                * Upload Course Review image.
                * */
                event.preventDefault();
                var index = event.currentTarget.getAttribute('data-index'),
                    reviews = this.model.get('review_info').reviews.slice(0),
                    review = reviews[index];

                var upload = new FileUploadModel({
                    title: gettext('Upload Image.'),
                    message: gettext('Files must be in JPEG or PNG format.'),
                    mimeTypes: ['image/jpeg', 'image/png']
                });
                var self = this;
                var modal = new FileUploadDialog({
                    model: upload,
                    onSuccess: function(response) {
                        review.image = response.asset.url;
                        self.model.set('review_info', {reviews: reviews});
                        self.model.trigger('change', self.model);
                        self.model.trigger('change:review_info', self.model);
                    }
                });
                modal.show();
            }
        });
        return ReviewInfoView;
    });
