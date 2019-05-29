Custom_string_toggle = function(first_string, second_string) {
    current = first_string;
    next = second_string;
    return function () {
        for_return = current;
        current = next;
        next = for_return;
        return for_return;
    }
};

hide_plus = Custom_string_toggle(" Hide advanced options", " Show advanced options");

$(".activity-show-advanced-options").on('click', function(e){
    $($(this).data('toggle')).toggle('slow');
    $('.activity-show-advanced-options .glyphicon').toggleClass('glyphicon-plus').toggleClass('glyphicon-minus');
    $(this).children(".button_description").text(hide_plus());
    event.preventDefault();
});