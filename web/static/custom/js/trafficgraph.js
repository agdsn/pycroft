/*!
 * Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */
function load_trafficchart(days) {
    var date_ago = function(delta) {
        /*
        Get the milliseconds of "today-delta".

        Example: Today is 2014-04-05, means 1396648800000, so
        we get 1396648800000-(delta*DAY_IN_MILLISECONDS) as result, which
        is the requested day at 0:00 in milliseconds.
         */
        var d = new Date(Date.now());
        d.setDate(d.getDate() - delta);
        d = Date.UTC(d.getFullYear(), d.getMonth(), d.getDate(), 0, 0, 0, 0);
        return d;
    };

    var format_date_to_string = function(d) {
        /*
        Input a Date object amd get a formatted string.
        Used in tooltips and the x-axis labels.
         */
        var day = d.getDate();
        var month = d.getMonth()+1;
        var year = d.getFullYear();
        return  ('0'+day).slice(-2) + '.' + ('0'+month).slice(-2) + '.' + year;
    };

    var DAY_IN_MILLISECONDS = 24*3600*1000;
    var DAYNAMES = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'];

    var trafficchart = new Highcharts.Chart({
        chart: {
            renderTo: 'trafficchart',
            type:'column',
            width: 700,
            height: 350,
            animation: false
        },
        title: {
            text: null
        },
        plotOptions: {
            series: {
                animation: false,
                pointStart: date_ago(days-1),
                pointInterval: DAY_IN_MILLISECONDS,
                groupPadding: 0.1
            }
        },
        legend: {
            enabled: false
        },
        tooltip: {
            formatter: function () {
                var date = new Date(this.x);
                var tooltip = DAYNAMES[date.getDay()] + ',<br/><b>' + format_date_to_string(date) + '</b>';
                $.each(this.points, function (i, point) {
                    tooltip += '<br />' + point.series.name + ': ' + point.y + ' MB';
                });
                return tooltip;
            },
            positioner: function(w, h, p) {
                return { x: (trafficchart.plotSizeX/2), y: trafficchart.plotTop };
            },
            enabled: true,
            shared: true,
            animation: false,
            crosshairs: {
                color: '#CFCFCF',
                width: 700/days
            }
        },
        xAxis: {
            type: 'datetime',
            tickInterval: DAY_IN_MILLISECONDS,
            labels: {
                enabled: days <= 7,
                formatter: function() {
                    var date = new Date(this.value);
                    return DAYNAMES[date.getDay()] + '<br>' + format_date_to_string(date);
                }
            }
        },
        yAxis: {
            title:{
                text: "Traffic in MB"
            }
        },
        series: []
    });

    $.getJSON($("#trafficchart").data("trafficurl")+'/'+days, null, function(response) {
        $(response.series).each(function(idx, data) {
            trafficchart.addSeries(data);
        });
    });
}
