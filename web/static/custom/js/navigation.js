/**
 * Created with PyCharm.
 * User: jan
 * Date: 01.07.12
 * Time: 03:45
 * To change this template use File | Settings | File Templates.
 */
!function ($) {
    var SubNavBar = function (element, options) {
        this.options = $.extend({
            fix_class:'subnav-fixed'
        }, options);
        this.window = $(window);
        this.doc = $(document);
        this.element = $(element);
        this.navTop = this.element.length && this.element.offset().top - 40;
        this.isFixed = 1;

        this.processScroll();

        this.element.on('click', $.proxy(this.processClick, this));
        this.window.on('scroll', $.proxy(this.processScroll, this));
    };

    SubNavBar.prototype = {
        constructor:SubNavBar,

        processScroll:function () {
            var scrollTop = this.window.scrollTop();
            if (scrollTop >= this.navTop && !this.isFixed) {
                this.isFixed = 1;
                this.element.addClass(this.options.fix_class);
            } else if (scrollTop <= this.navTop && this.isFixed) {
                this.isFixed = 0;
                this.element.removeClass(this.options.fix_class);
            }
        },

        processClick:function () {
            var $window = this.window,
                    $doc = this.doc;
            if (!this.isFixed) {
                setTimeout(function () {
                    if ($doc.height() >= $window.height() + $window.scrollTop() + 60)
                        $window.scrollTop($window.scrollTop() - 60);
                }, 10)
            } else {
                setTimeout(function () {
                    if ($doc.height() >= $window.height() + $window.scrollTop() + 22)
                        $window.scrollTop($window.scrollTop() - 22);
                }, 10)
            }
        }
    };

    $.fn.subNavBar = function (options) {
        return this.each(function () {
            if (undefined == $(this).data('subNavBar')) {
                var plugin = new SubNavBar(this, options);
                $(this).data('subNavBar', plugin);
            }
        });
    };

    $.fn.subNavBar.defaults = {fix_class:'subnav-fixed'};
    $.fn.subNavBar.Constructor = SubNavBar;

}(window.jQuery);