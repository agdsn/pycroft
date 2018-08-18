/*!
 * Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import d3 from 'd3';

d3.selectAll('[data-chart="balance"]', function() {
  var parent = d3.select(this);
  var _width = parent.node().getBoundingClientRect().width;
  var margin = {top: 20, right: 20, bottom: 30, left: 50},
      width = _width - margin.left - margin.right,
      height = 150 - margin.top - margin.bottom;

  var x = d3.time.scale()
      .range([0, width]);

  var y = d3.scale.linear()
      .range([height, 0]);

  var xAxis = d3.svg.axis()
      .scale(x)
      .orient("bottom")
      .tickFormat(timeFormat);

  var yAxis = d3.svg.axis()
      .scale(y)
      .orient("left")
      .tickFormat(de.numberFormat("$s"));

  var area_pos = d3.svg.area()
      .x(function(d) { return x(d.valid_on); })
      .y0(function(d) { return y(0); })
      .y1(function(d) { return d.balance>0 ? y(d.balance) : y(0);})
      .interpolate("step-after");

  var area_neg = d3.svg.area()
      .x(function(d) { return x(d.valid_on); })
      .y0(function(d) { return d.balance<0 ? y(d.balance) : y(0);})
      .y1(function(d) { return y(0);})
      .interpolate("step-after");

  var line = d3.svg.line()
      .x(function(d) { return x(d.valid_on); })
      .y(function(d) { return y(d.balance); })
      .interpolate("step-after");

  var svg = parent.append("svg")
     .attr("viewBox", "0 0 " +
           (width + margin.left + margin.right) + " " +
           (height+ margin.top + margin.bottom))
     .classed("svg-content-responsive", true)
    .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  d3.json(parent.attr("data-url"), function(error, resp) {
    if (error) throw error;

    data = resp.items;
    data.forEach(function(d) {
      d.valid_on = d3.time.format.iso.parse(d.valid_on);
      d.balance = +d.balance/100.; //converts string to number
    });

    today = new Date();
    first = data[0];
    last = data[data.length-1];
    // 'today' might be earlier than last valid_on though...
    data.push({'balance': last.balance, 'valid_on': today});
    data.splice(0, 0, {'balance': 0, 'valid_on': d3.time.day.offset(first.valid_on, -1)});

    x.domain(d3.extent(data, function(d) { return d.valid_on; }));
    y.domain(d3.extent(data, function(d) { return d.balance; }));

    svg.append("path")
        .datum(data)
        .attr("class", "area")
        .attr("class", "area-blue")
        .attr("d", area_pos);

    svg.append("path")
        .datum(data)
        .attr("class", "area")
        .attr("class", "area-red")
        .attr("d", area_neg);

    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);

    svg.append("g")
        .attr("class", "y axis")
        .call(yAxis)
      .append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", 6)
        .attr("dy", ".71em")
        .style("text-anchor", "end")
        .text("Saldo");

    svg.append("path")
        .datum(data)
        .attr("class", "line")
        .attr("d", line);
  });
});
