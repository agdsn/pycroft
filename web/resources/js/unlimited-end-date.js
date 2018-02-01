/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */
// disables the DatePicker field if the block is marked as unlimited

$(function() {
    var end = $(".form-field");
    var unlimited = end.find("[name='end-unlimited']");
    var update_state = function () {
        end.find("[name='end-date']").prop("disabled", unlimited.prop("checked"));
    };
    unlimited.on('click', update_state);
    update_state();
});
