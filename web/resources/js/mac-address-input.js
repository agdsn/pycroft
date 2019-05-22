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
!function ($) {
    $.fn.inputMacMask = function () {
        this.on("keyup", function (e) {
            var r = /([a-f0-9]{2})([a-f0-9]{2})/i,
                str = e.target.value.replace(/[^a-f0-9]/ig, "");

            while (r.test(str)) {
                str = str.replace(r, '$1' + ':' + '$2');
            }

            e.target.value = str.slice(0, 17).toLowerCase();

            var manufacturer_addon = $(e.target).closest('.input-group').find('.mac-manufacturer');

            if(e.target.value.length === 17){
                $.getJSON( $SCRIPT_ROOT + '/host/interface-manufacturer/' + e.target.value, function( data ){
                    if(data.manufacturer){
                        manufacturer_addon.text(data.manufacturer);
                    }
                });
            }else{
                manufacturer_addon.text('?');
            }
        });

        this.trigger('keyup');
    };

    $('[data-role=mac-address-input]').inputMacMask();
}(jQuery);
