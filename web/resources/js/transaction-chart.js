/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import $ from 'jquery';
import * as dc from 'dc';
import crossfilter from 'crossfilter';

$(() => {
    const dateFormat = d3.time.format('%Y-%m-%d');
    const parent = d3.select('[data-chart="transactions-overview"]');

    //todo custom reduce functions for server-side stuff
    const volumeChart = dc.barChart('#volume-chart');
    const valueChart = dc.compositeChart('#value-chart');
    const amountChart = dc.barChart(valueChart);
    const cumAmountChart = dc.lineChart(valueChart);
    const accountChart = dc.rowChart('#account-selector');
    const typeChart = dc.rowChart('#account-type-selector');
    const transactionTable = dc.dataTable('#transaction-table');
    const transactionCount = dc.dataCount(".dc-data-count");
    const params = (new URL(document.location)).searchParams;
    const dateMin = dateFormat.parse(params.get('after'));
    const dateMax = dateFormat.parse(params.get('before'));

    $("#reset-all").click(() => {
        dc.filterAll();
        dc.renderAll();
        return false;
    });
    $("#reset-volume-chart").click(() => {
        volumeChart.filterAll();
        dc.redrawAll();
        return false;
    });

    d3.json(parent.attr("data-url"), resp => {

        const data = resp.items;
        data.forEach(d => {
            d.dd = dateFormat.parse(d.valid_on);
            d.month = d3.time.month(d.dd);
        });

        const ndx = crossfilter(data);
        const all = ndx.groupAll();

        const transaction = ndx.dimension(d => d.account_id);
        const transactionGroup = transaction.groupAll();
        transactionCount
            .dimension(ndx)
            .group(transactionGroup);

        const account = ndx.dimension(d => d.account_id);
        const accountGroup = account.group();
        const accountCache = {"Others": "Other accounts"}; //dict of values cached
        const accountReq = new Set([]); //set of ids being requested

        // todo url_for
        const accountName = (acc_id, format_func, action_func) => {
            if (!(acc_id in accountCache)) {
                const href = "/finance/accounts/" + acc_id;
                if (!accountReq.has(acc_id)) {
                    accountReq.add(acc_id);
                    $.getJSON(href + "/json?limit=0", data => {
                        accountCache[acc_id] = data.name;
                        action_func(acc_id, data.name);
                    }).done(() => {
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
            .label(d => {
                const format_func = acc_id => "acc-" + acc_id;
                const action_func = (acc_id, replacement) => {
                    $('text:contains("' + format_func(acc_id) + '")').text(replacement);
                };
                return accountName(d.key, format_func, action_func);
            })
            .ordering(d => -d.value)
            .renderLabel(true)
            .xAxis().tickValues([]);

        const accountType = ndx.dimension(d => d.type);
        const accountTypeGroup = accountType.group();

        typeChart
            .height(300)
            .width(250)
            .dimension(accountType)
            .group(accountTypeGroup)
            .cap(10)
            .x(d3.scale.linear().range([1, 100]))
            .label(d => d.key + " (" + d.value + ")")
            .renderLabel(true)
            .xAxis().tickValues([]);

        const dateDimension = ndx.dimension(d => d.dd);
        const monthDimension = ndx.dimension(d => d.month);

        const dateAccessor = d => d.dd;
        let dateExtent = [];
        dateExtent = d3.extent(data, dateAccessor);
        if (!(dateMin === null)) {
            dateExtent[0] = dateMin;
        }
        if (!(dateMax === null)) {
            dateExtent[1] = dateMax;
        }


        const monthGroup = monthDimension.group().reduceCount();
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

        const valueGroup = monthDimension.group().reduceSum(d => d.amount);
        const cumValueGroup = {
            all: () => {
                let s = 0;
                const g = [];
                valueGroup.all().forEach((d, i) => {
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


        const descCache = {};
        const descReq = new Set([]);

        transactionTable
            .dimension(dateDimension)
            .columns([
                d => d.amount / 100. + "&#x202F;€",
                d => {
                    const format_func = acc_id => "<span id=\"acc-" + acc_id + "\"></span>";
                    const action_func = (acc_id, replacement) => {
                        $('#acc-' + acc_id).text(replacement);
                    };
                    return accountName(d.account_id, format_func, action_func);
                },
                d => d.type,
            ])

            .group(d => {
                const href = "/finance/transactions/" + d.id;
                // if building template is too slow, jquery may be executed
                // before document is generated :(
                let desc = "Link";
                if (!(d.id in descCache)) {
                    if (!descReq.has(d.id)) {
                        descReq.add(d.id);
                        $.getJSON(href + "/json", data => {
                            $('a[href="' + href + '"]').text(data.description);
                            descCache[d.id] = data.description;
                            descReq.delete(d.id);
                        });
                    }
                } else {
                    desc = descCache[d.id];
                }
                const date = d3.time.format("%Y-%m-%d")(d.dd);

                const link = `<a id="transaction-link" href="${href}">${desc}</a>`;
                return date + " " + link;
            })
            .sortBy(d => -d.id)
            .size(15);

        //TODO transaction value chart (count vs value)
        //TODO total value transacted chart (count vs value)

        dc.renderAll();
    });
});
