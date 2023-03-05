/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import $ from 'jquery';
import TimeAgo from 'javascript-time-ago'
import de from 'javascript-time-ago/locale/de'

$.extend($.fn.bootstrapTable.defaults, $.fn.bootstrapTable.locales['de-DE'])
$.extend($.fn.bootstrapTable.defaults.icons, {
    paginationSwitchDown: 'fa-caret-square-down',
    paginationSwitchUp: 'fa-caret-square-up',
    refresh: 'fa-sync',
    toggleOff: 'fa-toggle-off',
    toggleOn: 'fa-toggle-on',
    columns: 'fa-th-list',
    detailOpen: 'fa-plus',
    detailClose: 'fa-minus',
    fullscreen: 'fa-arrows-alt',
    search: 'fa-search',
    clearSearch: 'fa-trash',
});
TimeAgo.addDefaultLocale(de)
const timeAgo = new TimeAgo('de-DE')

export var faIcon = (icon) => `<span class="fa ${icon}"></span>`;

/**
 * Using the `coloredFormatter` on a column requires
 * `data-cell-style="tdRelativeCellStyle"` so the color stripe will be
 * positioned correctly!
 *
 * @param value - the JSON content of the current cell. It should be
 * of the format `{'value': "3,50€", "is_positive": true}`
 * @param row
 * @param index
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

const targetStr = new_tab => new_tab ? "_blank" : "";

export function linkFormatter(value, _row, _index) {
    if (!value) {
        return;
    }

    let target = targetStr(value.new_tab);
    const {href, title} = value;
    let content;

    if (value.glyphicon) {
        content = `${title} ${faIcon(value.glyphicon)}`;
    } else if (value.empty === true) {
        content = `<span class="text-muted">${title}</span>`;
    } else {
        content = title;
    }
    return `<a target="${target}" href="${href}">${content}</a>`;
}

linkFormatter.attributes = { sortName: 'title' };

/**
 *  Format an entry as a link or plain, depending on the value of
 * the 'type' field.  It can either be 'plain' or 'native'.
 */
export function userFormatter(value, row, index) {
    if (!value) {
        return;
    }
    if (value['type'] === 'plain') {
        return value['title'];
    } else if (value['type'] === 'native') {
        return linkFormatter(value, row, index);
    } else {
        console.error("The following object could not be formatted by a userLogger:", value);
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
            return `
                <a href="${value['href']}" class="btn ${value['btn_class']}" title="${value['tooltip']}">
                    <span class="badge rounded-pill bg-light text-dark">
                        ${value['icon'].map(faIcon).join("")}
                    </span>
                    ${value['title']}
                </a>
            `;
        } else {
            return `
                <a target="${target}" href="${value['href']}" class="btn ${value['btn_class']}" title="${value['title']}">
                    ${faIcon(value['icon'])}
                </a>
            `;
        }
    } else {
        return `
            <a target="${target}" href="${value['href']}" class="btn ${value['btn_class']}">${value['title']}</a>
        `;
    }
}

function humanByteSize(bytes, si) {
    const thresh = si ? 1000 : 1024;
    if(Math.abs(bytes) < thresh) {
        return `${bytes} B`;
    }
    const units = si
        ? ['kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
        : ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
    let u = -1;
    do {
        bytes /= thresh;
        ++u;
    } while(Math.abs(bytes) >= thresh && u < units.length - 1);
    return `${bytes.toFixed(1)} ${units[u]}`;
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
    if (Array.isArray(value)) {
        return value.map(v => btnFormatter(v, row, index)).join('&nbsp;');
    }
    return btnFormatter(value, row, index);
}

export function listFormatter(value, row, index) {
    if (!value) {
        return;
    }
    let ret = '<ul style="margin:0;">';
    if (typeof value == 'string') {
        console.error(
            "Received string in column which should receive listFormatter." +
            " Did you forget to set `data-escape=\"false\"`?"
        );
        return value;
    }
    for (const item of value) {
        ret += `<li>${item}</li>`;
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

export function relativeDateFormatter(value, row, index) {
    if (!value) {
        return;
    }
    const msecEpoch = value['timestamp'] * 1000;
    const date = new Date(msecEpoch);
    return `
        <span class="relative-date" title="${value['formatted']}" data-bs-toggle="tooltip" data-placement="bottom">
            ${(timeAgo.format(date))}
        </span>
    `;
}
dateFormatter.attributes = { sortName: 'timestamp' };

export function euroFormatter(value, row, index){
    const eur = parseFloat(value).toFixed(2).replace('.', ',');

    return `${eur} €`;
}

export function booleanFormatter(value, row, index) {
    return value ? '<i class="fa fa-check-circle text-success"></i>'
        : '<i class="fa fa-times-circle text-danger"></i>';
}

export function textWithBooleanFormatter(value, row, index) {
    let icon_true = value['icon_true'] || 'fa fa-check-circle'
    let icon_false = value['icon_false'] ||'fa fa-times-circle'

    if (value['bool']){
        return `<i class="${icon_true} text-success"></i> ${value['text']}`;
    }else{
        return `<i class="${icon_false} text-danger"></i> ${value['text']}`;
    }
}

export function financeRowFormatter(row, index) {
    return row && row['row_positive']
        ? {classes: 'table-success'}
        : {classes: 'table-danger'};
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


$(() => {
    let userPropSel = $('.userprop[data-property-name]');
    userPropSel.mouseenter(ev => {
        let propitem = ev.currentTarget;
        let propname = propitem.attributes['data-property-name'].value;
        console.log(`hovered ${propname}`);
        markGuiltyGroups(propname);
    });
    userPropSel.mouseleave(ev => {
        let propitem = ev.currentTarget;
        let propname = propitem.attributes['data-property-name'].value;
        console.log(`un-hovered ${propname}`);
        unmarkGuiltyGroups(propname);
    });

    let tbodySel = $('.membership-table tbody');
    tbodySel.on('mouseenter', 'tr', ev => {
        let groupRow = ev.currentTarget;
        let granted = groupRow.hasAttribute('data-row-grants')
            ? groupRow.attributes['data-row-grants'].value.split(' ')
            : [];
        console.log(`granted: ${granted}`);
        let denied = groupRow.hasAttribute('data-row-grants')
            ? groupRow.attributes['data-row-denies'].value.split(' ')
            : [];
        console.log(`denied: ${denied}`);

        let userprops = $('.userprop[data-property-name]').toArray();
        userprops.filter(prop => (
            prop.classList.contains('userprop-granted')
            && !granted.includes(prop.attributes['data-property-name'].value)
        ) || (
            prop.classList.contains('userprop-denied')
            && !denied.includes(prop.attributes['data-property-name'].value)
        )).forEach(prop => prop.classList.add('userprop-deemphasized'));
    });
    tbodySel.on('mouseleave', 'tr', ev => {
        $('.userprop[data-property-name]').toArray()
            .forEach(prop => prop.classList.remove('userprop-deemphasized'));
    });
});


export function markGuiltyGroups(attrName) {
    let rows = $('.membership-table tbody tr').toArray();
    let grantingRows = rows.filter(row => row.attributes['data-row-grants'].value.split(' ').includes(attrName));
    console.log(`Got ${grantingRows.length} rows granting ${attrName}`);
    grantingRows.forEach(row => row.setAttribute('data-row-guilty-for', 'grants'));
    let denyingRows = rows.filter(row => row.attributes['data-row-denies'].value.split(' ').includes(attrName));
    console.log(`Got ${denyingRows.length} rows denying ${attrName}`);
    denyingRows.forEach(row => row.setAttribute('data-row-guilty-for', 'denies'));
}

export function unmarkGuiltyGroups(attrName) {
    let rows = $('.membership-table tbody tr').toArray();
    console.log(`Removing all attributes from all ${rows.length} rows.`);
    rows.forEach(row => row.removeAttribute('data-row-guilty-for'));
}

/**
 * Replace occurrences of `ticket:<ticketid>` or `Ticket#<ticket number>` by links to tickets.agdsn.de
 * @param text the tet to be replaced
 * @returns the replaced text
 */
function withMagicLinksReplaced(text) {
    let replaced_text = text
        // ticket id
        .replace(new RegExp("ticket[:#]([0-9]{3,6})(?=\\b)", "ig"), "<a href=\"https://tickets.agdsn.de/index.pl?Action=AgentTicketZoom;TicketID=$1\">$&</a>")
        // ticket number (YYYYMMDDhhmmss¿¿)
        .replace(new RegExp("(?<=\\b)(ticket[:#])?([0-9]{16})(?=\\b)", "ig"), "<a href=\"https://tickets.agdsn.de/index.pl?Action=AgentTicketZoom;TicketNumber=$2\">Ticket#$2</a>")
    ;
    console.debug(`${text} ⇒ ${replaced_text}`);
    return replaced_text;
}

export function withMagicLinksFormatter(value, row, index) {
    if (!value) {
        return;
    }
    return withMagicLinksReplaced(value);
}

$('table').on('load-error.bs.table', function (e, status, res) {
    $("tr.no-records-found > td", this).html(`Error: Server returned HTTP ${status}.`);
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
!($ => {
    let BootstrapTable = $.fn.bootstrapTable.Constructor;
    let _initTable = BootstrapTable.prototype.initTable;
    let _initBody = BootstrapTable.prototype.initBody;
    let _initPagination = BootstrapTable.prototype.initPagination;

    BootstrapTable.prototype.initTable = function () {
        // Init sort name
        this.initSortName();

        //Initialize subtables
        if (this.options.loadSubtables){
            this.$container.find('table').on('expand-row.bs.table', (e, index, row, $detail) => {
                $detail.find('table').each((_, table) => {
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
        const header = this.$el.find('>thead');
        header.find('th').each(function () {
            const column = this;
            // Column already has a sort name
            if (column.hasAttribute("data-sort-name") || !column.hasAttribute('data-field'))
                return;

            // Lookup sort name in formatter attributes
            if (column.hasAttribute('data-formatter')) {
                const formatter = column.getAttribute('data-formatter');
                const attributes = $.fn.bootstrapTable.utils.calculateObjectValue(
                    column, `${formatter}.attributes`, [], null);

                if (attributes !== null && attributes.hasOwnProperty('sortName')) {
                    const sortName = `${column.getAttribute('data-field')}.${attributes.sortName}`;
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
})($);

/*
    detailFormatter for the host table, displaying the related interfaces
*/
export function hostDetailFormatter(index, row, element){
    let html = `<b>Interfaces</b><span class="float-right"><a href="${row.interface_create_link}" class="btn btn-primary btn-sm"><span class="fa fa-plus"></span> Interface</a></span>`;

    $.ajax({
         async: false,
         type: 'GET',
         url: row.interfaces_table_link,
         success: data => {
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

    $.each(row.parameters, (key, value) => {
        html = html.concat(`<code>${key}:</code> ${value}<br/>`);
    });

    if (row.errors.length) {
        html = html.concat(`<br/><h5><b>Fehlermeldungen</b></h5>`);

        $.each(row.errors, (key, value) => {
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
    const mapping = {
        "OPEN": 'table-warning',
        "EXECUTED": 'table-success',
        "FAILED": 'table-danger',
    }
    return {
        classes: mapping[row.status] || ""
    }
}

/*
    rowStyle for the membership requests
*/
export function membershipRequestRowFormatter(row){
    let cssclass = "";

    if(row.action_required){
        cssclass = "table-warning";
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

/**
 * Convert a property string like `~prop` into a red/green property badge.
 * @param value: string
 * @return string
 */
function propertyBadge(value) {
    const denied = value.startsWith("~");
    const info = denied ? {
        "propName": value.slice(1),
        "userPropClass": "userprop-denied",
        "spanTitle": "Granted, aber dann denied",
    } : {
        "propName": value,
        "userPropClass": "userprop-granted",
        "spanTitle": "Granted",
    };
    return `
        <span class="badge userprop ${info.userPropClass}"
           data-property-name="${info.propName}">
          <span title="${info.spanTitle}">${info.propName}</span>
        </span>
    `;
}

/**
 * Present a string of the form `foo ~bar ~baz` as red/green property badges.
 * @param value
 * @param row
 * @param index
 */
export function propertiesFormatter(value, row, index) {
    if (!value) { return; }
    return value.split(/\s+/).map(propertyBadge).join(" ");
}


export function ibanFormatter(value, row, index) {
    if (!value) { return; }
    const prefix = value.slice(0,4)
    const rest = value.slice(4)
    let res = prefix;

    for (let i = 0; i < rest.length / 4; i++) {
        res += `\u202f${rest.slice(4*i, 4*i+4)}`;
    }
    return res;
}



/**
 * Returns the type of the switch port name
 */
function getSwitchPortType(name) {
    if (name == null) {
        return false;
    }

    if (/^\d+$/.test(name)) {
        return 'numeric';
    } else if (/^[a-z]\d+$/.test(name.toLowerCase())) {
        return 'alphanumeric';
    } else if (/^\d+\/\d+\/\d+$/.test(name)) {
        return 'slash';
    } else {
        return false
    }
}

/**
 * Sort switch port names. Supports three schemes:
 * - A1, A2, ..., C20, C22
 * - 1, 2, 3, ..., 12, 13
 * - 1/1/1, 1/1/2, 2/1/1, 2/2/20
 */
export function sortPort(a, b) {
    const type_a = getSwitchPortType(a);
    const type_b = getSwitchPortType(b);

    if (type_a === type_b && type_a !== 'numeric') {
        if (type_a === 'alphanumeric') {
            const character_a = a[0];
            const character_b = b[0];
            const num_a = parseInt(a.substr(1));
            const num_b = parseInt(b.substr(1));

            if (character_a < character_b) {
                return -1;
            }
            if (character_a > character_b) {
                return 1;
            }

            if (num_a < num_b) {
                return -1;
            }
            if (num_a > num_b) {
                return 1;
            }

            return 0;
        }
        if (type_a === 'slash') {
            const split_a = a.split('/');
            const split_b = b.split('/');

            for (let i = 0; i < split_a.length; i++) {
                const num_a = parseInt(split_a[i]);
                const num_b = parseInt(split_b[i]);

                if (num_a < num_b) {
                    return -1;
                }
                if (num_a > num_b) {
                    return 1;
                }
            }

            return 0;
        }
    } else {
        if (type_a === type_b && type_a === 'numeric') {
            a = parseInt(a);
            b = parseInt(b);
        }

        if(a < b) { return -1; }
        if(a > b) { return 1; }
        return 0;
    }
}

export function cleanPortName(name) {
    if (name == null) {
        return null;
    }

    const match = name.match(/^\?\? \((.+)\)$/);

    if (match != null && match.length > 1) {
        return match[1];
    }

    return name;
}

export function sortPatchPort(a, b) {
    return sortPort(cleanPortName(a), cleanPortName(b));
}
