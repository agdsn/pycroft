/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

var users = new Bloodhound({
    name: 'users',
    datumTokenizer: (function () {
        var t = Bloodhound.tokenizers.whitespace;
        return function (r) {
            return t(r['name']).push(r['id'], r['login']);
        };
    })(),
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
        wildcard: '%QUERY',
        url: $SCRIPT_ROOT + '/user/json/search?query=%QUERY',
        ttl: 60,
        filter: function(response) { return response.users; },
    },
});

users.initialize();

$('#nav_search').typeahead({
    hint: true,
    highlight: true,
    minLength: 1,
    name: 'users',
    displayText: function(item) {
        return item['name'] + ' (' + item['id'] + ', ' + item['login'] + ')';
    },
    source: users.ttAdapter(),
    templates: {
        empty: '&nbsp;Keine Ergebnisse',
    },
    afterSelect: function(item) {
        window.location = $SCRIPT_ROOT + "/user/" + item.id;
    },
    selectOnBlur: false,
    showHintOnFocus: true,
});
