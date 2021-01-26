/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import $ from 'jquery';

/*
 * Activates all tooltips.
 * Non-Essential for page loading.
 * See https://getbootstrap.com/docs/4.6/components/tooltips/ */
$(function () {
    $('[data-toggle="tooltip"]').tooltip()
});
