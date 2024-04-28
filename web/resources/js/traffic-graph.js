/*!
 * Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import ApexCharts from 'apexcharts';
import { formatBytes } from 'bytes-formatter';

const options = {
    chart: {
        type: 'bar',
        stacked: true,
        height: 200,
        animations: {
            enabled: false,
        },
    },
    noData: "No data available.",
    legend: {
        position: 'right',
        offsetY: 40
    },
    plotOptions: {
        bar: { dataLabels: { total: { enabled: true } } }
    },
    xaxis: {
        type: "datetime",
        labels: {
            datetimeFormatter: {
                day: "ddd MM-dd"
            }
        },
    },
    yaxis: { labels: { formatter: formatBytes } },
    dataLabels: { formatter: formatBytes },
    colors: ["#1f77b4", "#b55d1f"],
}

function renderChart(el, json) {
    const chart = new ApexCharts(el, {
        ...options,
        series: [  // TODO transpose the JSON response on the backend
            { name: 'Download', data: json.map(x => x.ingress) },
            { name: 'Upload', data: json.map(x => x.egress) },
        ],
        xaxis: {
            ...options.xaxis,
            categories: json.map(x => x.timestamp),
        },
    })
    chart.render();
}

document.addEventListener('DOMContentLoaded', () => {
    const tabEl = document.getElementById('tab-traffic');
    if (!tabEl) {
        console.warning("No element of id tab-traffic exists!")
        return
    }
    tabEl.addEventListener('shown.bs.tab', () => {
        document.querySelectorAll(".traffic-graph").forEach(el => {
            const { url } = el.dataset;
            fetch(url)
                .then(data => data.json())
                .catch(e => console.log(e))
                .then(json => renderChart(el, json))
        })
    }, { once: true });
});
