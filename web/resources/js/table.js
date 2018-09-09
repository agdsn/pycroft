/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import _ from "underscore";
import $ from 'jquery';
import 'bootstrap-table';

export var linkTemplate = _.template(
    '<a href="<%= href %>"><%= title %></a>',
);

export var btnTemplate = _.template(
    '<a href="<%= href %>" class="btn <%= btn_class %>"><%= title %></a>',
);

export var glyphBtnTemplate = _.template(
    '<a href="<%= href %>" class="btn <%= btn_class %>" title="<%= title %>"><span class="glyphicon <%= glyphicon %>"></span></a>',
);

export var multiGlyphBtnTemplate = _.template(
    '<a href="<%= href %>" class="btn <%= btn_class %>" title="<%= tooltip %>">' +
    '<span class="badge">' +
    '<% for (var i = 0; i <= glyphicons.length; i++) { %>' +
    '<span class="glyphicon <%= glyphicons[i] %>"></span>' +
    '<% } %>' +
    '</span>' +
    '<%= title %>' +
    '</a>',
);

/**
 * Using the `coloredFormatter` on a column requires
 * `data-cell-style="tdRelativeCellStyle"` so the color stripe will be
 * positioned correctly!
 *
 * @param value - the JSON content of the current cell. It should be
 * of the format `{'value': "3,50€", "is_positive": true}`
 */
export function coloredFormatter(value, row, index) {
    if (!value) {
        return;
    }

    const class_name = value.is_positive  ? 'positive' : 'negative';

    return `${value['value']}<span class="table-stripe-right ${class_name}"></span>`;
}
coloredFormatter.attributes = { sortName: 'value' };

/**
 * This function makes the td `relative`.  It can be applied to a col
 * (`<th>`) via the `data-cell-style` attribute.
 *
 * The parameters are not used.
 */
export function tdRelativeCellStyle(value, row, index, field) {
    return {
        css: {"position": "relative"},
    };
}

export function linkFormatter(value, row, index) {
    if (!value) {
        return;
    }
    return linkTemplate({'href': value['href'], 'title': value['title']});
}
linkFormatter.attributes = { sortName: 'title' };

export function userFormatter(value, row, index) {
    /* Format an entry as a link or plain, depending on the value of
     * the 'type' field.  It can either be 'plain' or 'native'. */
    if (!value) {
        return;
    }
    if (value['type'] === 'plain') {
        return value['title'];
    } else if (value['type'] === 'native') {
        return linkFormatter(value, row, index);
    } else {
        console.log("ERROR: The following object could not be formatted by a userLogger:", value);
        return "Invalid format";
    }
}
userFormatter.attributes = { sortName: 'title' };

export function btnFormatter(value, row, index) {
    if (!value) {
        return;
    }
    if (value['icon']) {
        if (value['icon'] instanceof Array) {
            return multiGlyphBtnTemplate({
                'href': value['href'],
                'title': value['title'],
                'btn_class': value['btn_class'],
                'glyphicons': value['icon'],
                'tooltip': value['tooltip'],
            });
        } else {
            return glyphBtnTemplate({
                'href': value['href'],
                'title': value['title'],
                'btn_class': value['btn_class'],
                'glyphicon': value['icon'],
                'tooltip': value['tooltip'],
            });
        }
    } else {
        return btnTemplate({
            'href': value['href'],
            'title': value['title'],
            'btn_class': value['btn_class'],
            'tooltip': value['tooltip'],
        });
    }

}

export function multiBtnFormatter(value, row, index) {
    if (!value) {
        return;
    }
    return value.map(v => btnFormatter(v, row, index)).join('');
}

export function listFormatter(value, row, index) {
    if (!value) {
        return;
    }
    var ret = '<ul style="margin:0;">';
    for (var i = 0; i < value.length; i++) {
        ret += '<li>' + value[i] + '</li>';
    }
    ret += '</ul>';
    return ret;
}

export function dateFormatter(value, row, index) {
    if (!value) {
        return;
    }
    return value['formatted'];
}
dateFormatter.attributes = { sortName: 'timestamp' };

export function financeRowFormatter(row, index) {
    if (row && row['row_positive']) {
        return {classes: 'success'};
    } else {
        return {classes: 'danger'};
    }
}

$('table').on('load-error.bs.table', function (e, status, res) {
    $("tr.no-records-found > td", this).html("Error: Server returned HTTP " + status + ".");
});

$.extend($.fn.bootstrapTable.defaults, {
    responseHandler: response => response.items,
    classes: "table table-striped",
    pageSize: 20,
    cache: false,
    search: true,
    pagination: true,
});

/**
 * This bootstrap table extension adds the `data-sort-name` attribute to columns
 * that are formatted by a `data-formatter`. Therefor a formatter can specify a
 * `sortName`, which is used to derive the column's `data-sort-name` attribute.
 */
!function ($) {
    var BootstrapTable = $.fn.bootstrapTable.Constructor,
        _initTable = BootstrapTable.prototype.initTable;

    BootstrapTable.prototype.initTable = function () {
        // Init sort name
        this.initSortName();

        // Init Body
        _initTable.apply(this, Array.prototype.slice.apply(arguments));
    };

    // Init sort name
    BootstrapTable.prototype.initSortName = function () {
        var header = this.$el.find('>thead');
        header.find('th').each(function () {
            var column = this;
            // Column already has a sort name
            if (column.hasAttribute("data-sort-name") || !column.hasAttribute('data-field'))
                return;

            // Lookup sort name in formatter attributes
            if (column.hasAttribute('data-formatter')) {
                var formatter = column.getAttribute('data-formatter');
                var attributes = $.fn.bootstrapTable.utils.calculateObjectValue(
                    column, formatter + '.attributes', [], null);

                if (attributes !== null && attributes.hasOwnProperty('sortName')) {
                    var sortName = column.getAttribute('data-field') + "." + attributes.sortName;
                    column.setAttribute('data-sort-name', sortName);
                }
            }
        });
    };
}($);
