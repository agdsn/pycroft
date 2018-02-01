/*!
 * Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */
var de = d3.locale({
"decimal": ",",
"thousands": ".",
"grouping": [3],
"currency": ["", "€"],
"dateTime": "%a %b %e %X %Y",
"date": "%d.%m.%Y",
"time": "%H:%M:%S",
"periods": ["AM", "PM"],
"days": ["Sonntag", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"],
"shortDays": ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"],
"months": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"],
"shortMonths": ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Dez"]
});
var timeFormat = de.timeFormat.multi([
["%H:%M", function(d) { return d.getMinutes(); }],
["%H:%M", function(d) { return d.getHours(); }],
["%a %d", function(d) { return d.getDay() && d.getDate() != 1; }],
["%b %d", function(d) { return d.getDate() != 1; }],
["%B", function(d) { return d.getMonth(); }],
["%Y", function() { return true; }]
]);
