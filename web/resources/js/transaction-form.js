/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import $ from 'jquery';
import account_typeahead from './account-typeahead';

$(function () {
    var split_rows = $(".split-row");
    var next_id = split_rows.length;
    var row_prototype;
    var amount_fields = [];
    // Attach event handlers to buttons
    split_rows.find(".split-add-button").on("click", function (event) {
        // Clone row prototype
        var new_row = row_prototype.clone(true);
        var id_field = new_row.find("#splits-0-account_id");
        var typeahead_field = new_row.find("#splits-0-account");
        var amount_field = new_row.find("#splits-0-amount");
        // Set new ids
        id_field.attr({
            "id": "splits-" + next_id + "-account_id",
            "name": "splits-" + next_id + "-account_id",
        });
        typeahead_field.attr({
            "id": "splits-" + next_id + "-account",
            "name": "splits-" + next_id + "-account",
        });
        amount_field.attr({
            "id": "splits-" + next_id + "-amount",
            "name": "splits-" + next_id + "-amount",
        });
        // Enable typeahead
        account_typeahead(id_field, typeahead_field);
        amount_fields.push(amount_field);
        // Enable buttons
        new_row.find(".split-add-button").removeClass("hidden");
        new_row.find(".split-remove-button").removeClass("hidden");
        next_id++;
        // Add new row
        $(".split-row").last().after(new_row);
        // Hide the current add button
        $(event.target).addClass("hidden");
    });
    split_rows.find(".split-remove-button").on("click", function (event) {
        // Remove row with clicked button
        var split_row = $(event.target).parents(".split-row");
        split_row.remove();
        // Show add button in new last row
        $(".split-row").last().find(".split-add-button").removeClass("hidden");
    });
    // Clone after event handlers have been attached
    row_prototype = split_rows.first().clone(true);
    row_prototype.find("input").val('');
    // Activate typeahead on account fields after clone
    split_rows.each(function (index, element) {
        account_typeahead(
            $(element).find("#splits-" + index + "-account_id"),
            $(element).find("#splits-" + index + "-account"),
        );
    });
    // Show add button in last row
    split_rows.last().find(".split-add-button").removeClass("hidden");
});
