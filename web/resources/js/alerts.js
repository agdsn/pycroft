/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import $ from 'jquery';

$(function () {
    let isFixed = 0;
    const $window = $(window);
    const $subnav = $(".subnav");

    function place_alerts() {
        const $messages = $(".flash-messages");
        if (!$messages.length)
            return;
        const offset = $messages.offset().top;
        const top = $window.scrollTop();

        if (isFixed) {
            if (top < 2) {
                $messages.removeClass("flash-messages-fixed");
                $messages.css("margin-top", 0);
                isFixed = 0;
            }
            if ($subnav.length) {
                let padding = 28;
                if (top < 60) {
                    padding = (top / 2) - 2;
                }
                $messages.css("margin-top", padding);
            }
        } else {
            if (top >= 2) {
                const width = $messages.width();
                $messages.addClass("flash-messages-fixed");
                $messages.css("width", width);
                isFixed = 1;

                // reemit event as workaround to get proper subnav offset calc
                $window.trigger("scroll");
            }
        }
    }

    $window.on("scroll", place_alerts);
});
