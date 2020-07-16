/*!
 * Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

    export function format(value) {
        const exponent = Math.abs(value) > 1 ? Math.floor(Math.log(Math.abs(value)) / Math.log(1024)) : 0;
        const prefix = exponent ? "KMGTPEZY"[exponent - 1] + "iB" : "B";
        return Math.round((value / Math.pow(1024, exponent)) * 10) / 10 + " " + prefix;
    }

    export function ceil(value) {
        const exponent = Math.abs(value) > 1 ? Math.floor(Math.log(Math.abs(value)) / Math.log(1024)) : 0;
        const signum = value < 0 ? -1 : 1;
        return signum * (Math.ceil(Math.abs(value) / Math.pow(1024, exponent)) * Math.pow(1024, exponent));
    }

    /**
     * d3.scale.linear() but with a tick generation function optimized for binary prefixes.
     */
    export function linearScale() {
        const scale = d3.scale.linear();
        scale.ticks = function (m) {
            return d3.range.apply(d3, d3_scale_linearTickRange_binary(this.domain(), m));
        };

        const copyOrg = scale.copy;
        scale.copy = function () {
            const copied = copyOrg(this);
            copied.ticks = this.ticks;
            copied.copy = this.copy;
            return copied;
        };

        return scale;
    }

    function d3_scaleExtent(domain) {
        const start = domain[0], stop = domain[domain.length - 1];
        return start < stop ? [start, stop] : [stop, start];
    }

    function d3_scale_linearTickRange_binary(domain, m) {
        if (m === null) m = 10;

        const extent = d3_scaleExtent(domain);
        const span = extent[1] - extent[0];
        let step = Math.pow(2, Math.floor(Math.log(span / m) / Math.log(2)));
        const err = m / span * step;

        // Filter ticks to get closer to the desired count.
        if (err <= 0.20) step *= 8;
        else if (err <= 0.35) step *= 4;
        else if (err <= 0.75) step *= 2;

        // Round start and stop values to step interval.
        extent[0] = Math.ceil(extent[0] / step) * step;
        extent[1] = Math.floor(extent[1] / step) * step + step * 0.5; // inclusive
        extent[2] = step;
        return extent;
}
