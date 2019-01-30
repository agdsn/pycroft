/*!
 * Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details.
 */

import $ from 'jquery';

$.fn.fixedHeader = function (options) {
 var config = {
   topOffset: 40
   //bgColor: 'white'
 };
 if (options){ $.extend(config, options); }

 return this.each( function() {
  var o = $(this);

  var $win = $(window)
    , $head = $('thead.header', o)
    , isFixed = 0;
  var headTop = $head.length && $head.offset().top - config.topOffset;

  function processScroll() {
    if (!o.is(':visible')) return;
    if ($('thead.header-copy').length) {
      $('thead.header-copy').width($head.width());
      var i, scrollTop = $win.scrollTop();
    }
    var t = $head.length && $head.offset().top - config.topOffset;
    if (!isFixed && headTop !== t) { headTop = t; }
    if (scrollTop >= headTop && !isFixed) {
      isFixed = 1;
    } else if (scrollTop <= headTop && isFixed) {
      isFixed = 0;
    }
    isFixed ? $('thead.header-copy', o).show().offset({ left: $head.offset().left })
            : $('thead.header-copy', o).hide();
  }
  $win.on('scroll', processScroll);

  // hack sad times - holdover until rewrite for 2.1
  $head.on('click', function () {
    if (!isFixed) setTimeout(function () {  $win.scrollTop($win.scrollTop() - 47) }, 10);
  });

  $head.clone(true).removeClass('header').addClass('header-copy header-fixed').css({'position': 'fixed', 'top': config['topOffset']}).appendTo(o);
  o.find('thead.header-copy').width($head.width());

  o.find('thead.header > tr > th').each(function (i, h) {
    var w = $(h).width();
    o.find('thead.header-copy> tr > th:eq('+i+')').width(w)
  });
  $head.css({ margin:'0 auto',
              width: o.width(),
             'background-color':config.bgColor });
  processScroll();
 });
};

$(function() {
  $('.table-fixed-header').fixedHeader();
});
