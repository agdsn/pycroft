/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import _ from "underscore";
import $ from 'jquery';
import 'bootstrap-table';

export var linkTemplate = _.template(
    '<a target="<%- target %>"  href="<%- href %>"><%- title %></a>',
);

export var emptyLinkTemplate = _.template(
    '<a target="<%- target %>"  href="<%- href %>"><span class="text-muted"><%- empty_title %></span></a>',
);

export var glyphLinkTemplate = _.template(
    '<a target="<%- target %>"  href="<%- href %>"><%- title %> <span class="glyphicon <%- glyphicon %>"></span></a>',
);

export var btnTemplate = _.template(
    '<a target="<%- target %>"  href="<%- href %>" class="btn <%- btn_class %>"><%- title %></a>',
);

export var glyphBtnTemplate = _.template(
    '<a target="<%- target %>" href="<%- href %>" class="btn <%- btn_class %>" title="<%- title %>"><span class="glyphicon <%- glyphicon %>"></span></a>',
);

export var multiGlyphBtnTemplate = _.template(
    '<a href="<%- href %>" class="btn <%- btn_class %>" title="<%- tooltip %>">' +
    '<span class="badge">' +
    '<% for (var i = 0; i <= glyphicons.length; i++) { %>' +
    '<span class="glyphicon <%- glyphicons[i] %>"></span>' +
    '<% } %>' +
    '</span>' +
    '<%- title %>' +
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

    let target = "";

    if(value["new_tab"]){
        target = "_blank"
    }

    if(value["glyphicon"]){
        return glyphLinkTemplate({'href': value['href'], 'title': value['title'], 'target': target, 'glyphicon': value['glyphicon']});
    } else if (value['empty'] !== true) {
        return linkTemplate({'href': value['href'], 'title': value['title'], 'target': target});
    } else {
        return emptyLinkTemplate({'href': value['href'], 'empty_title': value['title'], 'target': target});
    }

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

    let target = "";

    if(value["new_tab"]){
        target = "_blank"
    }

    if (value['icon']) {
        if (value['icon'] instanceof Array) {
            return multiGlyphBtnTemplate({
                'href': value['href'],
                'title': value['title'],
                'btn_class': value['btn_class'],
                'glyphicons': value['icon'],
                'tooltip': value['tooltip'],
                'target': target,
            });
        } else {
            return glyphBtnTemplate({
                'href': value['href'],
                'title': value['title'],
                'btn_class': value['btn_class'],
                'glyphicon': value['icon'],
                'tooltip': value['tooltip'],
                'target': target,
            });
        }
    } else {
        return btnTemplate({
            'href': value['href'],
            'title': value['title'],
            'btn_class': value['btn_class'],
            'tooltip': value['tooltip'],
            'target': target,
        });
    }
}

function humanByteSize(bytes, si) {
    var thresh = si ? 1000 : 1024;
    if(Math.abs(bytes) < thresh) {
        return bytes + ' B';
    }
    var units = si
        ? ['kB','MB','GB','TB','PB','EB','ZB','YB']
        : ['KiB','MiB','GiB','TiB','PiB','EiB','ZiB','YiB'];
    var u = -1;
    do {
        bytes /= thresh;
        ++u;
    } while(Math.abs(bytes) >= thresh && u < units.length - 1);
    return bytes.toFixed(1)+' '+units[u];
}

export function byteFormatterBinary(value, row, indexx) {
    if (!value) {
        return;
    }

    return humanByteSize(value, false);
}

export function byteFormatter(value, row, indexx) {
    if (!value) {
        return;
    }

    return humanByteSize(value, true);
}

export function multiBtnFormatter(value, row, index) {
    if (!value) {
        return;
    }

    if (Array.isArray(value)){
        return value.map(v => btnFormatter(v, row, index)).join('&nbsp;');
    }else{
        return btnFormatter(value, row, index);
    }
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

export function euroFormatter(value, row, index){
    value = value.toFixed(2).replace('.', ',')

    return `${value} €`;
}

export function financeRowFormatter(row, index) {
    if (row && row['row_positive']) {
        return {classes: 'success'};
    } else {
        return {classes: 'danger'};
    }
}

export function membershipRowAttributes(row, index) {
    return {
        'data-row-grants': row.grants.join(' '),
        'data-row-denies': row.denies.join(' '),
    };
}

export function membershipRowFormatter(row, index) {
    if (row && !row.active) {
        return {classes: 'row-membership-inactive'};
    }
    return {};
}

$(function() {
    let userPropSel = $('.userprop[data-property-name]');
    userPropSel.mouseenter(function(ev) {
        let propitem = ev.currentTarget;
        let propname = propitem.attributes['data-property-name'].value;
        console.log("hovered " + propname);
        markGuiltyGroups(propname);
    });
    userPropSel.mouseleave(function(ev) {
        let propitem = ev.currentTarget;
        let propname = propitem.attributes['data-property-name'].value;
        console.log("un-hovered " + propname);
        unmarkGuiltyGroups(propname);
    });

    let tbodySel = $('.membership-table tbody');
    tbodySel.on('mouseenter', 'tr', function(ev) {
        let groupRow = ev.currentTarget;
        let granted = groupRow.hasAttribute('data-row-grants')
            ? groupRow.attributes['data-row-grants'].value.split(' ')
            : [];
        console.log("granted: " + granted);
        let denied = groupRow.hasAttribute('data-row-grants')
            ? groupRow.attributes['data-row-denies'].value.split(' ')
            : [];
        console.log("denied: " + denied);

        let userprops = $('.userprop[data-property-name]').toArray();
        userprops.filter(prop => (
            prop.classList.contains('userprop-granted')
            && !granted.includes(prop.attributes['data-property-name'].value)
        ) || (
            prop.classList.contains('userprop-denied')
            && !denied.includes(prop.attributes['data-property-name'].value)
        )).forEach(prop => prop.classList.add('userprop-deemphasized'));
    });
    tbodySel.on('mouseleave', 'tr', function(ev) {
        $('.userprop[data-property-name]').toArray()
            .forEach(prop => prop.classList.remove('userprop-deemphasized'));
    });
});


export function markGuiltyGroups(attrName) {
    let rows = $('.membership-table tbody tr').toArray();
    let grantingRows = rows.filter(row => row.attributes['data-row-grants'].value.split(' ').includes(attrName));
    console.log("Got " + grantingRows.length + " rows granting " + attrName);
    grantingRows.forEach(row => row.setAttribute('data-row-guilty-for', 'grants'));
    let denyingRows = rows.filter(row => row.attributes['data-row-denies'].value.split(' ').includes(attrName));
    console.log("Got " + denyingRows.length + " rows denying " + attrName);
    denyingRows.forEach(row => row.setAttribute('data-row-guilty-for', 'denies'));
}

export function unmarkGuiltyGroups(attrName) {
    let rows = $('.membership-table tbody tr').toArray();
    console.log("Removing all attributes from all " + rows.length + " rows.");
    rows.forEach(row => row.removeAttribute('data-row-guilty-for'));
}


$('table').on('load-error.bs.table', function (e, status, res) {
    $("tr.no-records-found > td", this).html("Error: Server returned HTTP " + status + ".");
});

$.extend($.fn.bootstrapTable.defaults, {
    responseHandler: response => response.items,
    classes: "table table-striped table-hover",
    pageSize: 20,
    cache: false,
    search: true,
    pagination: true,
    escape: true,
});


/**
 * Adds the expanded attribute to `true` on the first item
 */
export function userHostResponseHandler(resp) {
    let items = resp.items;
    if (items.length === 1) {
        let item = items[0];

        if (!item.hasOwnProperty('_data')) {
            item['_data'] = {};
        }

        item['_data']['expanded'] = true;
    }
    return items;
}


/**
 * This bootstrap table extension handles multiple extra attributes:
 *
 * Adds the `data-sort-name` attribute to columns
 * that are formatted by a `data-formatter`. Therefor a formatter can specify a
 * `sortName`, which is used to derive the column's `data-sort-name` attribute.
 *
 * If the `data-expanded` attribute is set to `true` on a row (for example by
 * adding it to the _data dict of the fetched data), a may available `detailView`
 * will be expanded by default.
 *
 * If the `data-hide-pagination-info` attribute is set to `true` on the table,
 * the pagination info will be hidden if there is only one page.
 *
 * If the `data-load-subtables` attributes is set to `true` on the table,
 * subtables in the detailView will be loaded.
 */
!function ($) {
    let BootstrapTable = $.fn.bootstrapTable.Constructor;
    let _initTable = BootstrapTable.prototype.initTable;
    let _initBody = BootstrapTable.prototype.initBody;
    let _initPagination = BootstrapTable.prototype.initPagination;

    BootstrapTable.prototype.initTable = function () {
        // Init sort name
        this.initSortName();

        //Initialize subtables
        if (this.options.loadSubtables){
            this.$container.find('table').on('expand-row.bs.table', function(e, index, row, $detail){
                $detail.find('table').each(function(_, table){
                    if ($(table).bootstrapTable('getOptions').length === 1){
                        $(table).bootstrapTable();
                    }
                })
            })
        }

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

    BootstrapTable.prototype.initBody = function () {
        _initBody.apply(this, Array.prototype.slice.apply(arguments));
        this.$body.find('> tr[data-index][data-expanded=true] > td > .detail-icon').click();
    };

    BootstrapTable.prototype.initPagination = function () {
        _initPagination.apply(this, Array.prototype.slice.apply(arguments));

        if (this.options.hidePaginationInfo && this.totalPages === 1) {
            this.$pagination.find('.pagination-info').hide();
        }
    }
}($);

/*
    detailFormatter for the host table, displaying the related interfaces
*/
export function hostDetailFormatter(index, row, element){
    let html = `<b>Interfaces</b><span class="pull-right"><a href="${row.interface_create_link}" class="btn btn-primary btn-xs"><span class="glyphicon glyphicon-plus"></span> Interface</a></span>`;

    $.ajax({
         async: false,
         type: 'GET',
         url: row.interfaces_table_link,
         success: function(data) {
              html = html.concat(data)
         }
    });

    return html;
}


/*
    detailFormatter for the task table, displaying the used parameters
*/
export function taskDetailFormatter(index, row, element){
    let html = '<h5><b>Verwendete Parameter</b></h5>';

    $.each(row.parameters, function(key, value) {
        html = html.concat(`<code>${key}:</code> ${value}<br/>`);
    });

    if (row.errors.length) {
        html = html.concat(`<br/><h5><b>Fehlermeldungen</b></h5>`);

        $.each(row.errors, function(key, value){
            html = html.concat(`<code>${value}</code><br/>`);
        });
    }

    html = html.concat(`<br/><i>Erstellt am ${row.created}</i>`);

    return html;
}

/*
    rowStyle for the task table, representing the status
*/
export function taskRowFormatter(row){
    let cssclass = "";

    if(row.status == "OPEN"){
        cssclass = "warning";
    }else if(row.status == "EXECUTED"){
        cssclass = "success";
    }else if(row.status == "FAILED"){
        cssclass = "danger";
    }

    return {
       classes: cssclass
    }
}

/*
    detailFormatter for the unmatched bank_account_activities table
 */

export function bankAccountActivitiesDetailFormatter(index, row, element){
    let html = `
        <b>IBAN:</b> ${row.iban}<br/>
        <b>Importiert am:</b> ${row.imported_at.formatted}
    `;

    return html;
}
