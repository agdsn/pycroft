var binaryPrefix = {};
!function() {
    binaryPrefix.format = function (value) {
        var exponent = Math.abs(value) > 1 ? Math.floor(Math.log(Math.abs(value)) / Math.log(1024)) : 0;
        var prefix = exponent ? "KMGTPEZY"[exponent - 1] + "iB" : "B";
        return Math.round((value / Math.pow(1024, exponent)) * 10) / 10 + " " + prefix;
    };

    binaryPrefix.ceil = function (value) {
        var exponent = Math.abs(value) > 1 ? Math.floor(Math.log(Math.abs(value)) / Math.log(1024)) : 0;
        var signum = value < 0 ? -1 : 1;
        return signum * (Math.ceil(Math.abs(value) / Math.pow(1024, exponent)) * Math.pow(1024, exponent));
    };

    /**
     * d3.scale.linear() but with a tick generation function optimized for binary prefixes.
     */
    binaryPrefix.linearScale = function () {
        scale = d3.scale.linear();
        scale.ticks = function (m) {
            return d3.range.apply(d3, d3_scale_linearTickRange_binary(this.domain(), m));
        };

        var copyOrg = scale.copy;
        scale.copy = function () {
            var copied = copyOrg(this);
            copied.ticks = this.ticks;
            copied.copy = this.copy;
            return copied;
        };

        return scale;
    };

    function d3_scaleExtent(domain) {
        var start = domain[0], stop = domain[domain.length - 1];
        return start < stop ? [start, stop] : [stop, start];
    }

    function d3_scale_linearTickRange_binary(domain, m) {
        if (m === null) m = 10;

        var extent = d3_scaleExtent(domain),
            span = extent[1] - extent[0],
            step = Math.pow(2, Math.floor(Math.log(span / m) / Math.log(2))),
            err = m / span * step;

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
}();