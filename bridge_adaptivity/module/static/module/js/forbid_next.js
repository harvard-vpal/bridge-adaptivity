(function(){
    var forbidNext = $("#next-button").data("forbidden");
    if (forbidNext){
        console.log("Current Activity is not answered, NEXT is forbidden!");
        $("#forbidNextModal").modal("show");
    }
}());

var enable_next_buttons = function () {
    $(".next-button-link button.disabled").removeClass("disabled");
    next_item = $("#next-button").data("next_item");
    $(".next-button-link").attr("href", next_item)
};

var update_ui_details = function(uiDetailsArray){

    ui_option_element = $("#ui_option");
    child_elements = ui_option_element.data("child_elements");
    child_classes = ui_option_element.data("child_classes");
    ui_option_element.empty();
    uiDetailsArray.forEach(function(ui_option){
        var new_element = document.createElement(child_elements);
        new_element.className = child_classes;
        new_element.innerHTML = ui_option;
        ui_option_element.append(new_element);
    })
};

(function() {
    sequence_item = $("#next-button").data("sequence_item");
    is_disabled = $("#next-button").data("is_disabled");
    enable_ui_option = $("#next-button").data("enable_ui_option");
    if(sequence_item && is_disabled){
        var ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
        var buttonSocket = new WebSocket(
            ws_scheme + '://' +  window.location.host + '/ws/sequence/'+ sequence_item + '/'
        );
         console.log("Next button channel run");
        buttonSocket.onmessage = function(e) {
            var data = JSON.parse(e.data);
            var message = data['result'];
            console.log("Next button channel: "+ message);
            if("sequence_status" in message) {
                enable_next_buttons();
            }
            if(enable_ui_option === true && "ui_details" in message){
                update_ui_details(message["ui_details"])
            }

        };
    } else {
        enable_next_buttons()
    }
}());
