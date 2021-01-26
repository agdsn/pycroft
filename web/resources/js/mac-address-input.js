/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import jQuery from 'jquery';

/**
 *  MAC-Mask
 *
 *  Adds format mask for MAC addresses on input fields.
 */

async function fetchManufacturerName(value) {
    if (value.length !== 17) { return '?'; }

    const resp = await fetch(`${$SCRIPT_ROOT}/host/interface-manufacturer/${value}`)
    return resp.json().then(data => {
        console.log("Received mac data: ", data);
        return data?.manufacturer ?? '?';
    });
}

!function ($) {
    $.fn.inputMacMask = function () {
        this.on("keyup", function (e) {
            const r = /([a-f0-9]{2})([a-f0-9]{2})/i;
            let str = e.target.value.replace(/[^a-f0-9]/ig, "");

            while (r.test(str)) {
                str = str.replace(r, "$1:$2");
            }

            e.target.value = str.slice(0, 17).toLowerCase();

            const manufacturer_addon = $(e.target).closest('.input-group').find('.mac-manufacturer');
            fetchManufacturerName(e.target.value)
                .then(manuf => manufacturer_addon.text(manuf))
        });

        this.trigger('keyup');
    };

    $('[data-role=mac-address-input]').inputMacMask();
}(jQuery);
