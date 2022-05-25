/*
 * Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details
 */

import * as td from "@eonasdan/tempus-dominus";

td.DefaultOptions.display ??= {};
td.DefaultOptions.display.components ??= {};
td.DefaultOptions.display.components.useTwentyfourHour = true;
td.DefaultOptions.allowInputToggle = true;

const selector = 'form [data-role=datetimepicker]';

document.addEventListener('DOMContentLoaded', () => {
    document
        .querySelectorAll<HTMLAnchorElement>(selector)
        .forEach(el => new td.TempusDominus(el))
});
