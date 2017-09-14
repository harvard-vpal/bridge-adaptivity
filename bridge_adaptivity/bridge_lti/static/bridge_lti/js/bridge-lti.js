(function ($) {
    $(function () {
        // LTI launch form auto-submission:
        var $element = $("#ltiLaunchForm");
        if ($element) {
            $element.submit();
        } else {
            console.error("Launch form for content preview can't be found!");
        }
    });
}(jQuery));
