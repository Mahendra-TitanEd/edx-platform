(function(define) {
    define(['backbone'], function(Backbone) {
        'use strict';

        return Backbone.Model.extend({
            defaults: {
                modes: [],
                course: '',
                enrollment_start: '',
                number: '',
                content: {
                    overview: '',
                    display_name: '',
                    number: '',
                    chapter_id:'',
                    is_new:'',
                    is_path_enrollment_end:''
                },
                start: '',
                image_url: '',
                org: '',
                id: '',
                topic: '',
                all: '',
                name: '',
                detail_url: '',
                instructors: '',
                hits: '',
                length: '',
                chapter_id:'',
                section_id:'',
                subsection_id:'',
                user_subscription: '',
                college_subscription: '',
                course_name: '',
                level: '',
                trial_course: '',
                free_course: '',
                sections:'',
                course_topic: '',
                url_section:'',
                location:'',
                is_new: '',
                is_recent:'',
                a_date:'',
                advertised_start:'',
                public_invitation_only:'',
                enroll_end_date: '',
                course_price: '',
                is_enrolled: ''
            }
        });
    });
}(define || RequireJS.define));
