/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import jQuery from 'jquery';

/**
 * The LazyLoadSelect plugin!
 *
 * This Plugin is used with the LazyLoadSelectField from web.form.fields.
 * It fetches new option values if one of the dependencies changes.
 */
!function ($) {

    var LazyLoadSelect = function (element, options) {
        this.element = $(element);
        this.options = $.extend({
            field_ids: [],
            item_attr: "items",
        }, options);
        this.fields = [];
        this.itemAttr = this.options.item_attr;
        this.dataUrl = this.element.data("url");

        var field_ids = [];
        if (undefined !== this.element.data("fieldids"))
            field_ids = field_ids.concat(this.element.data("fieldids").split(","));
        if (undefined !== this.options.field_ids)
            field_ids = field_ids.concat(this.options.field_ids);

        for (var i = 0; i < field_ids.length; i++) {
            this.fields.push($("#" + field_ids[i]));
        }
        this.bind();
    };

    LazyLoadSelect.prototype = {
        constructor: LazyLoadSelect,

        bind: function () {
            for (var i = 0; i < this.fields.length; i++) {
                this.fields[i].on("change", $.proxy(this.reload, this));
            }
        },

        queryData: function () {
            var query_data = {};
            for (var i = 0; i < this.fields.length; i++) {
                var field = this.fields[i];
                query_data[field.attr("id")] = field.val();
            }
            return query_data;
        },

        reload: function (ev, cb) {
            var self = this;
            $.getJSON(this.dataUrl, this.queryData(), function (data) {
                self.replaceOptions.call(self, data);
                if (cb) cb();
            });
        },

        replaceOptions: function (data) {
            var items = data[this.itemAttr];
            this.element.find("option").remove();
            for (var i = 0; i < items.length; i++) {
                if (typeof items[i] === 'object')
                    this.element.append('<option value="' + items[i][0] + '">' + items[i][1] + '</option>');
                else
                    this.element.append('<option value="' + items[i] + '">' + items[i] + '</option>');
            }

            if (!this.oldvalue_loaded) {
                this.oldvalue_loaded = true;
                this.element.val(this.element.attr("value"));
            }
        },
    };

    $.fn.lazyLoadSelect = function (options) {
        var toPreload = [];

        function loadNext() {
            var next = toPreload.shift();
            if (next) next.reload.call(next, null, loadNext);
        }

        var result = this.each(function () {
            if (undefined === $(this).data('lazyLoadSelect')) {
                var plugin = new LazyLoadSelect(this, options);
                $(this).data('lazyLoadSelect', plugin);
                toPreload.push(plugin);
            }
        });

        loadNext();

        return result;
    };

    $.fn.lazyLoadSelect.defaults = {};
    $.fn.lazyLoadSelect.Constructor = LazyLoadSelect;

    $('[data-role=lazy-load-select]').lazyLoadSelect();
}(jQuery);
