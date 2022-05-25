/*
 * Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details
 */

import * as td from "@eonasdan/tempus-dominus";
import {DateTime} from "@eonasdan/tempus-dominus";
import Dates from "@eonasdan/tempus-dominus/types/dates";
import Display from "@eonasdan/tempus-dominus/types/display";

td.DefaultOptions.display ??= {};
td.DefaultOptions.display.components ??= {};
td.DefaultOptions.display.components.useTwentyfourHour = true;
td.DefaultOptions.allowInputToggle = true;

interface TdClasses {
    TempusDominus: typeof td.TempusDominus,
    Dates: typeof Dates,
    Display: typeof Display,
}

class IsoPlugin {
    load(option: {}, tdClasses: TdClasses, tdFactory: any) {
        // See https://getdatepicker.com/6/plugins/ for some general examples
        tdClasses.Dates.prototype.formatInput = function (date: DateTime) {
            return date.toISOString();
        }
        tdClasses.Dates.prototype.parseInput = function (input: string) {
            return DateTime.convert(new Date(Date.parse(input)))
        }
    }
}

td.extend(new IsoPlugin(), {});

const selector = 'form [data-role=datetimepicker]';

document.addEventListener('DOMContentLoaded', () => {
    document
        .querySelectorAll<HTMLAnchorElement>(selector)
        .forEach(el => new td.TempusDominus(el))
});
