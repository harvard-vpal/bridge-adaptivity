(function ($) {
    $(document).ready(function () {
        // LTI launch form auto-submission:
        var $element = $("#ltiLaunchForm");
        if ($element.length) {
            $element.submit();
        } else {
            console.error("Launch form element for content preview can't be found!");
        }
    });
}(jQuery));
