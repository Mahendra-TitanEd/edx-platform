(function(define) {
    define([
        'jquery',
        'underscore',
        'backbone',
        'edx-ui-toolkit/js/utils/html-utils'
    ], function($, _, Backbone, HtmlUtils) {
        'use strict';

        return Backbone.View.extend({

            el: '.search-facets',
            events: {
                'click li button': 'selectOption',
                'click .show-less': 'collapse',
                'click .show-more': 'expand'
            },

            initialize: function(options) {
                this.meanings = options.meanings || {};
                this.$container = this.$el.find('.search-facets-lists');
                this.facetTpl = HtmlUtils.template($('#facet-tpl').html());
                this.facetOptionTpl = HtmlUtils.template($('#facet_option-tpl').html());
            },

            facetName: function(key) {
                return this.meanings[key] && this.meanings[key].name || key;
            },

            termName: function(facetKey, termKey) {
                return this.meanings[facetKey] &&
                this.meanings[facetKey].terms &&
                this.meanings[facetKey].terms[termKey] || termKey;
            },

            renderOptions: function(options) {
                return HtmlUtils.joinHtml.apply(this, _.map(options, function(option) {
                    var data = _.clone(option.attributes);
                    data.name = this.termName(data.facet, data.term);
                    return this.facetOptionTpl(data);
                }, this));
            },

            renderFacet: function(facetKey, options) {
                if(facetKey=='categories'){
                    return this.facetTpl({
                        name: facetKey,
                        displayName: this.facetName(facetKey),
                        optionsHtml: this.renderOptions(options),
                        listIsHuge: (options.length > 3)
                    });
                }else{
                    return this.facetTpl({
                        name: facetKey,
                        displayName: this.facetName(facetKey),
                        optionsHtml: this.renderOptions(options),
                        listIsHuge: (options.length > 10)
                    });
                }
            },

            render: function() {
                var grouped = this.collection.groupBy('facet');
                var newGrouped = {};
                if(grouped.topic){
                    newGrouped['topic'] = grouped.topic
                }
                if(grouped.all){
                    newGrouped['all'] = grouped.all
                }
                if(grouped.categories){
                    newGrouped['categories'] = grouped.categories
                }
                if(grouped.price){
                    newGrouped['price'] = grouped.price
                }
                if(grouped.course_status){
                    newGrouped['course_status'] = grouped.course_status
                }
                if(grouped.level){
                    newGrouped['level'] = grouped.level
                }
                if(grouped.language){
                    newGrouped['language'] = grouped.language
                }
                if(grouped.is_new){
                    newGrouped['is_new'] = grouped.is_new
                }
                if(grouped.tags){
                    newGrouped['tags'] = grouped.tags
                }
                var htmlSnippet = HtmlUtils.joinHtml.apply(
                    this, _.map(newGrouped, function(options, facetKey) {
                        if (options.length > 0) {
                            if (facetKey == "level"){
                                options = options.sort(function(a,b){return a.id.toLowerCase().localeCompare(b.id.toLowerCase());});
                                var new_options = []
                                if (options[0].attributes.term == "Advanced") {
                                    var first = options.shift();
                                    options.push(first)
                                }
                                return this.renderFacet(facetKey, options);
                            }
                            else if(facetKey == "all"){
                                options = options.sort(function(a,b){return b.id.length - a.id.length});
                                var new_types = []
                                var i;
                                Array.prototype.move = function (old_index, new_index) {
                                    if (new_index >= this.length) {
                                        var k = new_index - this.length;
                                        while ((k--) + 1) {
                                            this.push(undefined);
                                        }
                                    }
                                    this.splice(new_index, 0, this.splice(old_index, 1)[0]);
                                    // return this; // for testing purposes
                                };
                                for (i = 0; i < options.length; i++) { 
                                    if (options[i].attributes.term == "Free Trial Talks"){
                                        options.move(i, options.length-1);
                                        continue;
                                    }
                                }
                                for (i = 0; i < options.length; i++) { 
                                    if(options[i].attributes.term == "Free Trial Courses"){
                                        options.move(i, options.length-1);
                                        continue;
                                    }
                                }
                                return this.renderFacet(facetKey, options);
                            }
                            else{
                                options = options.sort(function(a,b){return a.id.toLowerCase().localeCompare(b.id.toLowerCase());});
                                return this.renderFacet(facetKey, options);
                            }
                        }
                    }, this)
                );
                HtmlUtils.setHtml(this.$container, htmlSnippet);
                return this;
            },

            collapse: function(event) {
                var $el = $(event.currentTarget),
                    $more = $el.siblings('.show-more'),
                    $ul = $el.parent().siblings('ul');

                $ul.addClass('collapse');
                $el.addClass('hidden');
                $more.removeClass('hidden');
            },

            expand: function(event) {
                var $el = $(event.currentTarget),
                    $ul = $el.parent('div').siblings('ul');

                $el.addClass('hidden');
                $ul.removeClass('collapse');
                $el.siblings('.show-less').removeClass('hidden');
            },

            selectOption: function(event) {
                var $target = $(event.currentTarget);
                this.trigger(
                'selectOption',
                $target.data('facet'),
                $target.data('value'),
                $target.data('text')
            );
            }

        });
    });
}(define || RequireJS.define));
