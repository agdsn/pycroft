/*!
 * Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import _ from 'underscore';
import $ from 'jquery';
import 'autocomplete.js/src/jquery/plugin'
import Bloodhound from 'typeahead.js/dist/bloodhound';

    // Store typeahead variable in a closure
    export const system_accounts = new Bloodhound({
        name: 'system_accounts',
        datumTokenizer: Bloodhound.tokenizers.obj.whitespace('account_name'),
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        prefetch: {
            url: $SCRIPT_ROOT + '/finance/json/accounts/system',
            ttl: 60,
            transform: response => response.accounts,
        },
    });

    export const user_accounts = new Bloodhound({
        name: 'user_accounts',
        datumTokenizer: (function () {
            const t = Bloodhound.tokenizers.whitespace;
            return function (r) {
                return t(r['user_name']).push(r['user_id'], r['user_login']);
            };
        })(),
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
            url: $SCRIPT_ROOT + '/finance/json/accounts/user-search?query=%QUERY',
            ttl: 60,
            transform: response => response.accounts,
            wildcard: '%QUERY'
        },
    });

    system_accounts.initialize();
    user_accounts.initialize();

    const options = {
        hint: true,
        minLength: 1,
    };

    export const system_accounts_dataset = {
        name: 'system_accounts',
        displayKey: 'account_name',
        source: system_accounts.ttAdapter(),
        templates: {
            empty: '<span class="disabled">Keine Ergebnisse</span>',
            header: '<span class="dropdown-header">Systemkonten</span>',
            footer: '<span class="dropdown-divider"></span>',
        },
    };

    export const user_accounts_dataset = {
        name: 'user_accounts',
        displayKey: record => `${_.escape(record['user_name'])} (${record['user_id']}, ${_.escape(record['user_login'])})`,
        source: (query, cb) => user_accounts.ttAdapter()(query, cb, cb),
        templates: {
            empty: '<span class="disabled">Keine Ergebnisse</span>',
            header: '<span class="dropdown-header">Nutzerkonten</span>',
        },
    };

    export default function account_typeahead(id_field, typeahead_field) {
        typeahead_field.autocomplete(
            options, system_accounts_dataset, user_accounts_dataset,
        ).on('autocomplete:selected', function (event, item, dataset) {
            id_field.val(item['account_id']);
        });
    }

// Automatically enable account typeahead
$(function() {
    $('[data-toggle="account-typeahead"]').each(function () {
        const $typeahead_field = $(this);
        const target = $typeahead_field.attr('data-target');
        const $id_field = $(document.getElementById(target));
        account_typeahead($id_field, $typeahead_field);
    });
});
