// include `module/js/work_with_cookie.js` in template before using this script

function enable_next_buttons() {
    $(".next-button-link button.disabled").removeClass("disabled");
    next_item = $("#next-button").data("next_item");
    $(".next-button-link").attr("href", next_item)
}

function update_ui_details(uiDetailsArray) {
    ui_option_element = $("#ui_option");
    child_elements = ui_option_element.data("child_elements");
    child_classes = ui_option_element.data("child_classes");
    ui_option_element.empty();
    uiDetailsArray.forEach(function(ui_option) {
        let new_element = document.createElement(child_elements);
        new_element.className = child_classes;
        new_element.innerHTML = ui_option;
        ui_option_element.append(new_element);
    })
}

function show_congratulation_pop_up(congratulation_cookie_name){
    if(!getCookie(congratulation_cookie_name)) {
       $("#congratulationMessage").modal("show");
       setCookie(congratulation_cookie_name, true, 15);
    }
}

(function() {
    sequence_item = $("#next-button").data("sequence_item");
    is_disabled = $("#next-button").data("is_disabled");
    enable_ui_option = $("#next-button").data("enable_ui_option");

    let is_enable_next_button = !(sequence_item && is_disabled);
    if(is_enable_next_button) {
        enable_next_buttons();
    }
    if(sequence_item) {
        let ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
        let buttonSocket = new WebSocket(
            ws_scheme + '://' + window.location.host + '/ws/sequence/' + sequence_item + '/'
        );
        console.log("Next button channel run");
        buttonSocket.onmessage = function (e) {
            let data = JSON.parse(e.data);
            let message = data['result'];
            console.log("Next button channel: " + message);

            let congratulation_cookie_name = "congratulation_viewed";
            if ("is_show_pop_up" in message && message['is_show_pop_up']) {
                show_congratulation_pop_up(congratulation_cookie_name);
            } else {
                deleteCookie(congratulation_cookie_name);
            }

            if (!is_enable_next_button && "is_button_enable" in message && message['is_button_enable']) {
                enable_next_buttons();
            }

            if (enable_ui_option === true && "ui_details" in message) {
                update_ui_details(message["ui_details"])
            }
        };
    }
}());
