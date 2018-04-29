/*!
 * Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */
/**
 * form.js
 *
 * This file contains javascript code used with the forms
 *
 * copyright (c) 2012, 2014 AG DSN.
 */

/**
 * This is a today-button to use with the datepicker.
 */

!function ( $ ) {

    // Today Button object
    var TodayButton = function (element, options) {
        this.element = $(element);
        this.target = $("#" + this.element.data("target"));
        this.datepicker = this.target.data("datepicker");
        this.dateFormat = this.datepicker.format;

        this.element.on('click', $.proxy(this.click, this));
    };

    TodayButton.prototype = {
        constructor:TodayButton,

        click:function (ev) {
            ev.preventDefault();
            this.target.val(this.formatDate(new Date()));
            this.datepicker.update();
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
            if (undefined === $(this).data('todayButton')) {
                var plugin = new TodayButton(this, options);
                $(this).data('todayButton', plugin);
            }
        });
    };

    $.fn.todayButton.defaults = {};
    $.fn.todayButton.Constructor = TodayButton;

}(jQuery);

/**
 * AutoLoadFocus
 *
 * Automatically focuses the first input element of the first input group after
 * loading the page.
 */

$(function(){
    $(".form-group:first .controls:first :first").focus();
});

/**
 * IntervalPicker
 *
 * This Function is used by the IntervalField from web.form.fields.custom.
 * It shows some input-fields to create a well formatted interval.
 *
 * IntervalField is the id of the input-field representing the interval
 */
function pycroftIntervalPicker(IntervalField){
    if(!$('#'+IntervalField).next().is('.pycroftIntervalPicker')){
        // initial view of form --> create
        $('#'+IntervalField).after("<div id=\""+IntervalField+"Picker\" class=\"pycroftIntervalPicker\">" +
            '<a id="'+IntervalField+'CloseBtn" href="javascript:void(0)" class="closeBtn">X</a>' +
            '<input id="'+IntervalField+'PickerY" type="number" min="0" value="0"> Jahre ' +
            '<input id="'+IntervalField+'PickerM" type="number" min="0" max="12" value="0"> Monate ' +
            '<input id="'+IntervalField+'PickerD" type="number" min="0" max="31" value="0"> Tage<br>' +
            '<input id="'+IntervalField+'PickerH" type="number" min="0" max="23" value="0"> Std. ' +
            '<input id="'+IntervalField+'PickerI" type="number" min="0" max="59" value="0"> Min. ' +
            '<input id="'+IntervalField+'PickerS" type="number" min="0" max="59" value="0"> Sek.<br>' +
            '<button type="button" id="'+IntervalField+'PickerBtn">OK</button>' +
            "</div>");
        $('#'+IntervalField+'PickerBtn').click(function(){
            // close form
            $('#'+IntervalField+'Picker').css('display','none');
            // write current values to input-field
            // format:  0 years 0 mons 0 days 0 hours 0 mins 0 secs
            $('#'+IntervalField).val(
                $('#'+IntervalField+'PickerY').val() + ' years ' +
                $('#'+IntervalField+'PickerM').val() + ' mons ' +
                $('#'+IntervalField+'PickerD').val() + ' days ' +
                $('#'+IntervalField+'PickerH').val() + ' hours ' +
                $('#'+IntervalField+'PickerI').val() + ' mins ' +
                $('#'+IntervalField+'PickerS').val() + ' secs'
            );
        });
        $('#'+IntervalField+'CloseBtn').click(function(){
            // close form without applying any changes
            $('#'+IntervalField+'Picker').css('display','none');
        });
    }else{
       // show form again
       $('#'+IntervalField+'Picker').css('display','block');
    }

    // Fill form with current values
    var data = $('#'+IntervalField).val().split(' ');
    $('#'+IntervalField+'PickerY').val(data[0]);
    $('#'+IntervalField+'PickerM').val(data[2]);
    $('#'+IntervalField+'PickerD').val(data[4]);
    $('#'+IntervalField+'PickerH').val(data[6]);
    $('#'+IntervalField+'PickerI').val(data[8]);
    $('#'+IntervalField+'PickerS').val(data[10]);
}

/**
 *  MAC-Mask
 *
 *  Adds format mask for MAC addresses on input fields.
 */

function inputMacMask(selector){
    selector.on("keyup", function(e){
        var r = /([a-f0-9]{2})([a-f0-9]{2})/i,
            str = e.target.value.replace(/[^a-f0-9]/ig, "");

        while (r.test(str)) {
            str = str.replace(r, '$1' + ':' + '$2');
        }

        e.target.value = str.slice(0, 17).toLowerCase();
    });

    selector.trigger('keyup');
}
