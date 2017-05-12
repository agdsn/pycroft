/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */
function responseHandler(response) {
    return response.items;
}

var linkTemplate = _.template(
    '<a href="<%= href %>"><%= title %></a>'
);

var btnTemplate = _.template(
    '<a href="<%= href %>" class="btn <%= btn_class %>"><%= title %></a>'
);

var glyphBtnTemplate = _.template(
    '<a href="<%= href %>" class="btn <%= btn_class %>" title="<%= title %>"><span class="glyphicon <%= glyphicon %>"></span></a>'
);

var multiGlyphBtnTemplate = _.template(
    '<a href="<%= href %>" class="btn <%= btn_class %>">' +
        '<span class="badge">' +
        '<% for (var i = 0; i <= glyphicons.length; i++) { %>' +
            '<span class="glyphicon <%= glyphicons[i] %>"></span>' +
        '<% } %>' +
        '</span>' +
        '<%= title %>' +
    '</a>'
);

function linkFormatter(value, row, index) {
    return linkTemplate({'href': value['href'], 'title': value['title']})
}

function userFormatter(value, row, index) {
    /* Format an entry as a link or plain, depending on the value of
     * the 'type' field.  It can either be 'plain' or 'native'. */
    if (value['type'] == 'plain') {
        return value['title']
    } else if (value['type'] == 'native') {
        return linkFormatter(value, row, index)
    } else {
        console.log("ERROR: The following object could not be formatted by a userLogger:", value)
        return "Invalid format"
    }
}

function btnFormatter(value, row, index) {
    if (value['icon']) {
        if (value['icon'] instanceof Array) {
            return multiGlyphBtnTemplate({
                'href': value['href'],
                'title': value['title'],
                'btn_class': value['btn_class'],
                'glyphicons': value['icon']
            })
        } else {
            return glyphBtnTemplate({
                'href': value['href'],
                'title': value['title'],
                'btn_class': value['btn_class'],
                'glyphicon': value['icon']
            })
        }
    } else {
        return btnTemplate({
            'href': value['href'],
            'title': value['title'],
            'btn_class': value['btn_class']
        })
    }

}

function multiBtnFormatter(value, row, index) {
    var ret = '';
    for (var i = 0; i < value.length; i++) {
        ret += btnFormatter(value[i], row, index)
    }
    return ret
}

function listFormatter(value, row, index) {
    var ret = '<ul>';
    for (var i = 0; i < value.length; i++) {
        if (value[i].length == 0) {
            // If no list: put out the content
            ret += '<li>' + value[i] + '</li>';
        } else {
            // Else: Make first element strong
            ret += '<li><strong>' + value[i][0] + ': </strong>';
            for (var j = 1; j < value[i].length; j++) {
                ret += '<span>' + value[i][j] + '</span>'
            }
            ret += '</span></li>';
        }
    }
    ret += '</ul>';
    return ret
}

function financeRowFormatter(row, index) {
    if (row && row['row_positive']) {
        return {classes: 'success'};
    } else {
        return {classes: 'danger'};
    }
}
