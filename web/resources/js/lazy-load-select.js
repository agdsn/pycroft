/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import jQuery from 'jquery';

/**
 * The LazyLoadSelect plugin!
 *
 * This Plugin is used with the LazyLoadSelectField from wtforms_widgets.fields.
 * It fetches new option values if one of the dependencies changes.
 */
!function ($) {

    class LazyLoadSelect {
        constructor(element, options) {
            this.element = $(element);
            this.options = {
                field_ids: [],
                item_attr: "items",
                ...options
            }
            this.itemAttr = this.options.item_attr;
            this.dataUrl = this.element.data("url");

            let field_ids = [];
            if (undefined !== this.element.data("fieldids"))
                field_ids = field_ids.concat(this.element.data("fieldids").split(","));
            if (undefined !== this.options.field_ids)
                field_ids = field_ids.concat(this.options.field_ids);
            this.fields = field_ids.map(id => document.getElementById(id));

            this.bind();
        }

        bind() {
            this.fields.forEach(f => f.on("change", $.proxy(this.reload, this)));
        }

        queryData() {
            return Object.fromEntries(
                this.fields.map(f => [f.attr("id"), f.val()])
            );
        }

        reload(ev, cb) {
            const self = this;
            $.getJSON(this.dataUrl, this.queryData(), function (data) {
                self.replaceOptions.call(self, data, ev);
                if (cb) cb();
            });
        }

        replaceOptions(data, ev) {
            this.element.find("option").remove();

            data[this.itemAttr]
                .map(item => typeof item === 'object' ? item : [item, item])
                .map(([val, desc]) => `<option value="${val}">${desc}</option>`)
                .forEach(item => this.element.append(item));

            if (!this.oldvalue_loaded) {
                this.oldvalue_loaded = true;
                this.element.val(this.element.attr("value"));
            }

            if (ev?.originalEvent) {
                this.element.trigger('change');
            }
        }
    }


    $.fn.lazyLoadSelect = function (options) {
        let toPreload = [];

        function loadNext() {
            let next = toPreload.shift();
            if (next) next.reload.call(next, null, loadNext);
        }

        const result = this.each(function () {
            if (undefined === $(this).data('lazyLoadSelect')) {
                const plugin = new LazyLoadSelect(this, options);
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
