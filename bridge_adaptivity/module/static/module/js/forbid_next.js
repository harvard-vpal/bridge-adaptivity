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

(function() {
    room_name = $("#next-button").data("room_name");
    is_disabled = $("#next-button").data("is_disabled");
    if(room_name && is_disabled){
        var ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
        var buttonSocket = new WebSocket(ws_scheme + '://' +  window.location.host + '/sequence/'+ room_name + '/');
         console.log("Next button channel run");
        buttonSocket.onmessage = function(e) {
            var data = JSON.parse(e.data);
            var message = data['result'];
            console.log("Next button channel: "+ message);
            enable_next_buttons()
        };
    } else {
        enable_next_buttons()
    }
}());


