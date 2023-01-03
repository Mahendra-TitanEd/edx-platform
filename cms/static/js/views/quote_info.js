// Backbone Application View: Quote Information

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
        var QuoteInfoView = Backbone.View.extend({

            events: {
                'click .remove-quote-data': 'removeQuote',
                'click .action-upload-quote-image': 'uploadQuoteImage'
            },

            initialize: function() {
                // Set up the initial state of the attributes set for this model instance
                _.bindAll(this, 'render');
                this.template = this.loadTemplate('course-quote-details');
                this.listenTo(this.model, 'change:quote_info', this.render);
            },

            loadTemplate: function(name) {
                // Retrieve the corresponding template for this model
                return TemplateUtils.loadTemplate(name);
            },

            render: function() {
                var attributes;
                // Assemble the render view for this model.
                $('.course-quote-details-fields').empty();
                var self = this;
                $.each(this.model.get('quote_info').quotes, function(index, data) {
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

            removeQuote: function(event) {
                /*
                 * Remove course Quote fields.
                 * */
                event.preventDefault();
                var index = event.currentTarget.getAttribute('data-index'),
                    quotes = this.model.get('quote_info').quotes.slice(0);
                quotes.splice(index, 1);
                this.model.set('quote_info', {quotes: quotes});
            },

            uploadQuoteImage: function(event) {
                /*
                * Upload Quote image.
                * */
                event.preventDefault();
                var index = event.currentTarget.getAttribute('data-index'),
                    quotes = this.model.get('quote_info').quotes.slice(0),
                    quote = quotes[index];

                var upload = new FileUploadModel({
                    title: gettext('Upload Image.'),
                    message: gettext('Files must be in JPEG or PNG format.'),
                    mimeTypes: ['image/jpeg', 'image/png']
                });
                var self = this;
                var modal = new FileUploadDialog({
                    model: upload,
                    onSuccess: function(response) {
                        quote.image = response.asset.url;
                        self.model.set('quote_info', {quotes: quotes});
                        self.model.trigger('change', self.model);
                        self.model.trigger('change:quote_info', self.model);
                    }
                });
                modal.show();
            }
        });
        return QuoteInfoView;
    });
