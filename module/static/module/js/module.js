$(document).ready(function(){

    // next activity button
    var next_button = $('#button-next');
    
    // on click, disable the button for 2 seconds
    next_button.click(function(event){
        event.preventDefault();
        next_button.addClass('disabled');
        next_button.text('Loading...');
        setTimeout(afterTimeout, 2000);
    });

    // after timeout, follow the next activity link
    function afterTimeout(){
        window.location = next_button.attr('href');
    }

});