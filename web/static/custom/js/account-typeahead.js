var account_typeahead = (function() {
    // Store typeahead variable in a closure
    var system_accounts = new Bloodhound({
        name: 'system_accounts',
        datumTokenizer: Bloodhound.tokenizers.obj.whitespace('account_name'),
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        prefetch: {
            url: $SCRIPT_ROOT + '/finance/json/accounts/system',
            ttl: 60,
            filter: function(response) { return response.accounts; }
        }
    });
    var user_accounts = new Bloodhound({
        name: 'user_accounts',
        datumTokenizer: (function() {
            var t = Bloodhound.tokenizers.whitespace;
            return function(r) { return t(r['user_name']).push(r['user_id']); };
        })(),
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
            url: $SCRIPT_ROOT + '/finance/json/accounts/user-search?query=%QUERY',
            ttl: 60,
            filter: function(response) { return response.accounts; }
        }
    });
    system_accounts.initialize();
    user_accounts.initialize();
    var options = {
        hint: true,
        highlight: true,
        minLength: 1
    };
    var system_accounts_dataset = {
        name: 'system_accounts',
        displayKey: 'account_name',
        source: system_accounts.ttAdapter(),
        templates: {
            empty: '<span class="disabled">Keine Ergebnisse</span>',
            header: '<span class="dropdown-header">Systemkonten</span>',
            footer: '<span class="divider"></span>'
        }
    };
    var user_accounts_dataset = {
        name: 'user_accounts',
        displayKey: function (record) {
            return record['user_name'] + ' (' + record['user_id'] + ')';
        },
        source: user_accounts.ttAdapter(),
        templates: {
            empty: '<span class="disabled">Keine Ergebnisse</span>',
            header: '<span class="dropdown-header">Nutzerkonten</span>'
        }
    };
    return function(id_field, typeahead_field) {
        typeahead_field.typeahead(
            options, system_accounts_dataset, user_accounts_dataset
        ).on('typeahead:selected', function (event, item, dataset) {
            id_field.val(item['account_id']);
        });
    }
})();
