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

function linkFormatter(value, row, index) {
    return linkTemplate({'href': value['href'], 'title': value['title']})
}
