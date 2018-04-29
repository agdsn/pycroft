/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

$(function () {
    var dateFormat = d3.time.format('%Y-%m-%d');

    //todo custom reduce functions for server-side stuff
    var volumeChart = dc.barChart('#volume-chart');
    var valueChart = dc.compositeChart('#value-chart');
    var amountChart = dc.barChart(valueChart);
    var cumAmountChart = dc.lineChart(valueChart);
    var accountChart = dc.rowChart('#account-selector');
    var typeChart = dc.rowChart('#account-type-selector');
    var transactionTable = dc.dataTable('#transaction-table');
    var transactionCount = dc.dataCount(".dc-data-count");
    var params = (new URL(document.location)).searchParams;
    var dateMin = dateFormat.parse(params.get('after'));
    var dateMax = dateFormat.parse(params.get('before'));

    $("#reset-all").click(function () {
        dc.filterAll();
        dc.renderAll();
        return false;
    });
    $("#reset-volume-chart").click(function () {
        volumeChart.filterAll();
        dc.redrawAll();
        return false;
    });

    var url = new URL($SCRIPT_ROOT + '/transactions/json');
    url.search = document.location.search;
    d3.json(url.toString(), function (resp) {

        data = resp.items;
        data.forEach(function (d) {
            d.dd = dateFormat.parse(d.valid_on);
            d.month = d3.time.month(d.dd);
        });

        var ndx = crossfilter(data);
        var all = ndx.groupAll();

        var transaction = ndx.dimension(function (d) {
            return d.account_id;
        });
        var transactionGroup = transaction.groupAll();
        transactionCount
            .dimension(ndx)
            .group(transactionGroup);

        var account = ndx.dimension(function (d) {
            return d.account_id;
        });
        var accountGroup = account.group();
        var accountCache = {"Others": "Other accounts"}; //dict of values cached
        var accountReq = new Set([]); //set of ids being requested

        // todo url_for
        var accountName = function (acc_id, format_func, action_func) {
            if (!(acc_id in accountCache)) {
                var href = "/finance/accounts/" + acc_id;
                if (!accountReq.has(acc_id)) {
                    accountReq.add(acc_id);
                    jQuery.getJSON(href + "/json?limit=0", function (data) {
                        accountCache[acc_id] = data.name;
                        action_func(acc_id, data.name);
                    }).complete(function () {
                        accountReq.delete(acc_id);
                    });
                }
                return format_func(acc_id);
            } else {
                return accountCache[acc_id];
            }
        };

        accountChart
            .height(300)
            .width(250)
            .dimension(account)
            .group(accountGroup)
            .cap(10)
            .x(d3.scale.linear().range([1, 100]))
            .label(function (d) {
                var format_func = function (acc_id) {
                    return "acc-" + acc_id;
                };
                var action_func = function (acc_id, replacement) {
                    jQuery('text:contains("' + format_func(acc_id) + '")').text(replacement);
                };
                return accountName(d.key, format_func, action_func);
            })
            .ordering(function (d) {
                return -d.value;
            })
            .renderLabel(true)
            .xAxis().tickValues([]);

        var accountType = ndx.dimension(function (d) {
            return d.type;
        });
        var accountTypeGroup = accountType.group();

        typeChart
            .height(300)
            .width(250)
            .dimension(accountType)
            .group(accountTypeGroup)
            .cap(10)
            .x(d3.scale.linear().range([1, 100]))
            .label(function (d) {
                return d.key + " (" + d.value + ")";
            })
            .renderLabel(true)
            .xAxis().tickValues([]);

        var dateDimension = ndx.dimension(function (d) {
            return d.dd;
        });
        var monthDimension = ndx.dimension(function (d) {
            return d.month;
        });

        var dateAccessor = function (d) {
            return d.dd;
        };
        dateExtent = [];
        dateExtent = d3.extent(data, dateAccessor);
        if (!(dateMin === null)) {
            dateExtent[0] = dateMin;
        }
        if (!(dateMax === null)) {
            dateExtent[1] = dateMax;
        }


        var monthGroup = monthDimension.group().reduceCount();
        volumeChart
            .width(700)
            .height(100)
            .dimension(monthDimension)
            .group(monthGroup)
            .x(d3.time.scale().domain(dateExtent))
            .gap(0) // gap(0) has overlaps for some reason
            .xUnits(d3.time.months) //seems to be buggy, so we can't set bar width :(
            // logscale would also be nice, but that too is buggy
            .elasticY(true)
            .margins({top: 0, left: 70, right: 70, bottom: 25})
            .renderHorizontalGridLines(true)
            .renderVerticalGridLines(true)
            .yAxisLabel("# transactions");

        var valueGroup = monthDimension.group().reduceSum(function (d) {
            return d.amount;
        });
        var cumValueGroup = {
            all: function () {
                var s = 0;
                var g = [];
                valueGroup.all().forEach(function (d, i) {
                    s += d.value;
                    g.push({key: d.key, value: s});
                });
                return g;
            },
        };

        amountChart
            .dimension(monthDimension)
            .group(valueGroup, "Monthly amount transacted");

        cumAmountChart
            .dimension(monthDimension)
            .group(cumValueGroup, "Cumulative amount transacted")
            .ordinalColors(["orange"])
            .useRightYAxis(true)
            .interpolate("step-after");

        valueChart
            .width(700)
            .height(200)
            .dimension(monthDimension)
            .x(d3.time.scale().domain(dateExtent))
            .xUnits(d3.time.months)
            .elasticY(true)
            .brushOn(false)
            .margins({top: 0, left: 70, right: 70, bottom: 25})
            .renderHorizontalGridLines(true)
            .renderVerticalGridLines(true)
            .yAxisLabel("monthly net amount transacted")
            .rightYAxisLabel("total net amount transacted")
            .rangeChart(volumeChart)
            .legend(dc.legend().x(90).y(0).itemHeight(13).gap(5))
            .compose([amountChart, cumAmountChart]);


        var linkTemplate = _.template(
            '<a id="<%= id %>" href="<%= href %>"><%= title %></a>',
        );

        var descCache = {};
        var descReq = new Set([]);

        transactionTable
            .dimension(dateDimension)
            .columns([
                function (d) {
                    return d.amount / 100. + "&#x202F;€";
                },
                function (d) {
                    var format_func = function (acc_id) {
                        return "<span id=\"acc-" + acc_id + "\"></span>";
                    };
                    var action_func = function (acc_id, replacement) {
                        jQuery('#acc-' + acc_id).text(replacement);
                    };
                    return accountName(d.account_id, format_func, action_func);
                },
                function (d) {
                    return d.type;
                },
            ])

            .group(function (d) {
                var href = "/finance/transactions/" + d.id;
                // if building template is too slow, jquery may be executed
                // before document is generated :(
                var desc = "Link";
                if (!(d.id in descCache)) {
                    if (!descReq.has(d.id)) {
                        descReq.add(d.id);
                        jQuery.getJSON(href + "/json", function (data) {
                            jQuery('a[href="' + href + '"]').text(data.description);
                            descCache[d.id] = data.description;
                            descReq.delete(d.id);
                        });
                    }
                } else {
                    desc = descCache[d.id];
                }
                var date = d3.time.format("%Y-%m-%d")(d.dd);
                var link = linkTemplate({
                    'id': "transaction-link",
                    'href': href,
                    'title': desc,
                });
                return date + " " + link;
            })
            .sortBy(function (d) {
                return -d.id;
            })
            .size(15);

        //TODO transaction value chart (count vs value)
        //TODO total value transacted chart (count vs value)

        dc.renderAll();
    });
});
