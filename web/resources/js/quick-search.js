/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import _ from "underscore";
import $ from 'jquery';
import 'autocomplete.js/src/jquery/plugin'
import Bloodhound from 'typeahead.js/dist/bloodhound';

export const users = new Bloodhound({
    name: 'users',
    datumTokenizer: r => {
        return Bloodhound.tokenizers.whitespace(r['name']).push(r['id'], r['login']);
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
        wildcard: '%QUERY',
        url: `${$SCRIPT_ROOT}/user/json/search?query=%QUERY`,
        ttl: 60,
        transform: response => response.items,
    },
});

users.initialize();

const dataSource = users.ttAdapter();

$('#nav_search').autocomplete({
    hint: true,
    minLength: 1,
    templates: {

    },
}, {
    name: 'users',
    displayKey: item => `${_.escape(item['name'])} (${item['id']}, ${_.escape(item['login'])})`,
    source: (query, cb) => dataSource(query, cb, cb),
    templates: {
        empty: '<span>Keine Ergebnisse</span>',
    },
    classNames: {

    },
    //debounce: 250,
    autoselect: true,
    autoselectOnBlur: true,
    openOnFocus: true,
}).on('autocomplete:selected', (e, user) => {
    window.location = user.url.href;
});
