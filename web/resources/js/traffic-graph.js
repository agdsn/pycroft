/*!
 * Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import $ from 'jquery';
// TODO fix once we have a replacement
nv = {addGraph: _ => ({})}
import * as binaryPrefix from './binary-prefix';

$(() => {
    const dateFormat = d3.time.format('%Y-%m-%d');

    function setChartSize(graph) {
        const width = graph.parent.node().getBoundingClientRect().width;
        const height = 200;

        graph.chart
            .width(width)
            .height(height);

        graph.data
            .attr('width', width)
            .attr('height', height);
    }

    const el = document.getElementById('tab-traffic');
    if (!el) {
        console.warning("No element of id tab-traffic exists!")
        return
    }
    el.addEventListener('shown.bs.tab', () => {
        d3.select(".traffic-graph").each(function () {
            const trafficGraph = {
                parent: d3.select(this),
                url: this.dataset.url,
                days: this.dataset.days,
            };

            nv.addGraph({
                generate: () => {
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
                callback: graph => {
                    nv.utils.windowResize(() => {
                        setChartSize(trafficGraph);

                        trafficGraph.data
                            .transition().duration(0)
                            .call(graph);
                    });

                    loadTrafficData(trafficGraph);
                },
            });
        });
    }, {once: true});

    function loadTrafficData(trafficGraph) {
        d3.json(`${trafficGraph.url}/${trafficGraph.days}`,
            (error, resp) => {
            if (error) throw error;

            // Normalize data
            const traffic = resp;
            traffic.forEach(d => {
                d.timestamp = d3.time.format.iso.parse(d.timestamp);
            });

            // Traffic graph
            const data = [{
                key: "Upload",
                nonStackable: false,
                values: traffic.map(d => ({
                    x: d.timestamp,
                    y: d.egress,
                })),
            },
                {
                    key: "Download",
                    nonStackable: false,
                    values: traffic.map(d => ({
                        x: d.timestamp,
                        y: d.ingress,
                    })),
                }];

            trafficGraph.chart.xAxis.tickFormat(d => dateFormat(d));

            if (!traffic.some(d => !!d.ingress || !!d.egress))
                trafficGraph.chart.forceY([0, 1000]);

            trafficGraph.data.datum(data).transition().duration(250).call(trafficGraph.chart);
        });
    }

    const selectDays = document.querySelector('.select-days');
    if (!selectDays) {
        // TODO find out why that field does not exist anymore
        console.warn("No element of selector `.select-days`!");
        return
    }
    selectDays.addEventListener('change', ev => loadTrafficData(ev.target));
});
