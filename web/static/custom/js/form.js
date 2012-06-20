/*!
 * Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */
/**
 * form.js
 *
 * This file contains javascript code used with the forms
 *
 * copyright (c) 2012 by AG DSN.
 */

/**
 * This is a today-button to use with the datepicker.
 */
!function ( $ ) {

    // Today Button object
    var TodayButton = function (element, options) {
        this.element = $(element);
        this.target = $("#" + this.element.data("target"));
        this.datepicker = this.target.data("datepicker")
        this.dateFormat = this.datepicker.format;

        this.element.on('click', $.proxy(this.click, this));
    };

    TodayButton.prototype = {
        constructor:TodayButton,

        click:function (ev) {
            ev.preventDefault();
            this.target.val(this.formatDate(new Date()));
            this.datepicker.update()
        },

        formatDate:function (date) {
            var val = {
                d:date.getDate(),
                m:date.getMonth() + 1,
                yy:date.getFullYear().toString().substring(2),
                yyyy:date.getFullYear()
            };
            val.dd = (val.d < 10 ? '0' : '') + val.d;
            val.mm = (val.m < 10 ? '0' : '') + val.m;
            var date = [];
            for (var i = 0, cnt = this.dateFormat.parts.length; i < cnt; i++) {
                date.push(val[this.dateFormat.parts[i]]);
            }
            return date.join(this.dateFormat.separator);
        }
    };

    $.fn.todayButton = function (options) {
        return this.each(function () {
            if (undefined == $(this).data('todayButton')) {
                var plugin = new TodayButton(this, options);
                $(this).data('todayButton', plugin);
            }
        });
    };

    $.fn.todayButton.defaults = {};
	$.fn.todayButton.Constructor = TodayButton;

}(window.jQuery);

