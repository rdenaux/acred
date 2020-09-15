(function ($) {
    'use strict';
    jQuery('body').find('.wpcp-carousel-section.wpcp-standard').each(function () {

        var carousel_id = $(this).attr('id');
        var _this = $(this);

        if (jQuery().slick) {

            jQuery('#' + carousel_id).slick({
                prevArrow: '<div class="slick-prev"><i class="fa fa-angle-left"></i></div>',
                nextArrow: '<div class="slick-next"><i class="fa fa-angle-right"></i></div>',
                lazyLoad: 'ondemand',
            });
        }
    });
})(jQuery);