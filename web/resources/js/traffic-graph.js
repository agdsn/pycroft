/*!
 * Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import $ from 'jquery';
import nv from 'nvd3';
import * as binaryPrefix from './binary-prefix';

$(function() {
    var dateFormat = d3.time.format('%Y-%m-%d');

    function setChartSize(graph) {
        var width = graph.parent.node().getBoundingClientRect().width;
        var height = 200;

        console.log(width);

        graph.chart
            .width(width)
            .height(height);

        graph.data
            .attr('width', width)
            .attr('height', height);
    }

    $("#tab-traffic").one('shown.bs.tab', function () {
        d3.select(".traffic-graph").each(function () {
            var trafficGraph = {
                parent: d3.select(this),
                url: this.dataset.url,
                days: this.dataset.days,
            };

            nv.addGraph({
                generate: function () {
                    trafficGraph.chart = nv.models.multiBarChart()
                        .margin({top: 25, right: 75, bottom: 30, left: 60})
                        .stacked(true)
                        .groupSpacing(0.4)
                        .color(["#b55d1f", "#1f77b4"]);
                    trafficGraph.chart.yScale(binaryPrefix.linearScale());
                    trafficGraph.chart.yAxis.tickFormat(binaryPrefix.format);

                    trafficGraph.data = trafficGraph.parent.append("svg");

                    setChartSize(trafficGraph);

                    return trafficGraph.chart;
                },
                callback: function (graph) {
                    nv.utils.windowResize(function () {
                        setChartSize(trafficGraph);

                        trafficGraph.data
                            .transition().duration(0)
                            .call(graph);
                    });

                    loadTrafficData(trafficGraph);
                },
            });
        });
    });

    function loadTrafficData(trafficGraph) {
        var days = trafficGraph.days;
        var url = trafficGraph.url;
        d3.json(url + "/" + days, function (error, resp) {
            if (error) throw error;

            // Normalize data
            var traffic = resp.items.traffic;
            traffic.forEach(function (d) {
                d.timestamp = d3.time.format.iso.parse(d.timestamp);
            });

            // Traffic graph
            var data = [{
                key: "Upload",
                nonStackable: false,
                values: traffic.map(function (d) {
                    return {
                        x: d.timestamp,
                        y: d.egress,
                    };
                }),
            },
            {
                key: "Download",
                nonStackable: false,
                values: traffic.map(function (d) {
                    return {
                        x: d.timestamp,
                        y: d.ingress,
                    };
                }),
            }];

            trafficGraph.chart.xAxis.tickFormat(function (d) {
                return dateFormat(d);
            });

            if (!traffic.some(function (d) {
                return !!d.ingress || !!d.egress;
            }))
                trafficGraph.chart.forceY([0, 1000]);

            trafficGraph.data.datum(data).transition().duration(250).call(trafficGraph.chart);
        });
    }

    $('.select-days').on("change", function () {
        loadTrafficData(this);
    });
});
