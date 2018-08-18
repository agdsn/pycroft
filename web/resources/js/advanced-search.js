/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import $ from 'jquery';
import _ from 'underscore';
import {inputMacMask} from "./form";

$(function() {
    const $form = $('.form-basic');
    const $results = $('#results');

    inputMacMask($('#mac'));

    function refreshTable() {
        const params = {};

        $form.find('input,select').each(function (key, obj) {
            params[$(obj).attr("name")] = $(obj).val();
        });

        $results.bootstrapTable('refresh', {query: params});
    }

    $form.find('input').keyup(_.debounce(refreshTable, 250));
    $form.find('select').change(_.debounce(refreshTable, 250));
    refreshTable();
});
