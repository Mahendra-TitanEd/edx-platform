(function(define) {
    define(['jquery', 'backbone', 'gettext'], function($, Backbone, gettext) {
        'use strict';

        return Backbone.View.extend({

            el: '#discovery-form',
            events: {
                'submit form': 'submitForm'
            },

            initialize: function() {
                this.$searchField = this.$el.find('input');
                this.$searchButton = this.$el.find('button');
                this.$message = this.$el.find('#discovery-message');
                this.$loadingIndicator = this.$el.find('#loading-indicator');
            },

            submitForm: function(event) {
                event.preventDefault();
                this.doSearch();
            },

            doSearch: function(term) {
                if (term !== undefined) {
                    this.$searchField.val(term);
                } else {
                    term = this.$searchField.val();
                }
                this.trigger('search', $.trim(term));
            },

            clearSearch: function() {
                this.$searchField.val('');
            },

            showLoadingIndicator: function() {
                this.$loadingIndicator.removeClass('hidden');
            },

            hideLoadingIndicator: function() {
                this.$loadingIndicator.addClass('hidden');
            },

            showFoundMessage: function(count) {
                var msg = ngettext(
                '<h3> Showing %s result </h3>',
                '<h3> Showing %s results </h3>',
                count
            );
                this.$message.html(interpolate(msg, [count]));
            },

            showNotFoundMessage: function(term) {
                var msg = interpolate(
                gettext('<h3> We couldn\'t find any results for "%s".</h3>'),
                [_.escape(term)]
            );
                this.$message.html(msg);
                this.clearSearch();
            },

            showErrorMessage: function(error) {
                this.$message.text(gettext(error || '<h3>There was an error, try searching again.</h3>'));
            }

        });
    });
}(define || RequireJS.define));
