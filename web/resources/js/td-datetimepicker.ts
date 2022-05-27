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
/** Initialize TempusDominus on all elements with `[data-role=datetimepicker]`. */
function InitTdDatetimePickers() {
    document
        .querySelectorAll<HTMLElement>(selector)
        .forEach(el => new td.TempusDominus(el));
}

const linkedStartSelector = 'form [data-role=datetimepicker-start]'

/** Initialize TempusDominus and Eventhook on all elements with `[data-role=datetimepicker-start]`.
 *
 * You need to reference the picker for the end date
 * via `data-td-datetimepicker-end=$end_id`.
 * */
function InitTdRangePickers() {
    document
        .querySelectorAll<HTMLElement>(linkedStartSelector)
        .forEach(
            elStart => {
                const idEnd = elStart.dataset?.tdDatetimepickerEnd;
                if (!idEnd) {
                    console.error(
                        "Datetimepicker marked as `datetimepicker-start`" +
                        " is missing value for `data-td-datetimepicker-end`."
                    )
                    return;
                }
                const elEnd = document.getElementById(idEnd);
                if (!elEnd) {
                    console.error(
                        `Referenced datetimepicker #${idEnd} does not exist`
                    )
                }

                const pickerStart = new td.TempusDominus(elStart);
                const pickerEnd = new td.TempusDominus(elEnd!, {
                    useCurrent: false,
                });
                elStart.addEventListener(td.Namespace.events.change, e => {
                    pickerEnd.updateOptions({
                        restrictions: {
                            minDate: (e as CustomEvent).detail.date
                        }
                    });
                });
                elEnd!.addEventListener(td.Namespace.events.change, e => {
                    pickerStart.updateOptions({
                        restrictions: {
                            maxDate: (e as CustomEvent).detail.date
                        }
                    });
                });
            }
        )
}

document.addEventListener('DOMContentLoaded', () => {
    InitTdDatetimePickers();
    InitTdRangePickers();
});
