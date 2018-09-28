import jQuery from 'jquery';

/**
 *  Select-Multiple Improvement
 *
 *  Removes the obligation to hold CTRL when selecting multiple items
 */

!function ($) {
    $('select[multiple] option').mousedown(function(e) {
        e.preventDefault();
        $(this).prop('selected', !$(this).prop('selected'));
        return false;
    });
}(jQuery);