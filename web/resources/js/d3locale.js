/*!
 * Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

const de = d3.locale({
    decimal: ",",
    thousands: ".",
    grouping: [3],
    currency: ["", "€"],
    dateTime: "%a %b %e %X %Y",
    date: "%d.%m.%Y",
    time: "%H:%M:%S",
    periods: ["AM", "PM"],
    days: ["Sonntag", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"],
    shortDays: ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"],
    months: ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"],
    shortMonths: ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Dez"],
});

const timeFormat = de.timeFormat.multi([
    ["%H:%M", d => d.getMinutes()],
    ["%H:%M", d => d.getHours()],
    ["%a %d", d => d.getDay() && d.getDate() !== 1],
    ["%b %d", d => d.getDate() !== 1],
    ["%B", d => d.getMonth()],
    ["%Y", () => true],
]);

export {timeFormat, de};
