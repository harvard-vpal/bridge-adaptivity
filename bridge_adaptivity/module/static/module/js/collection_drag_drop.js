// include base_drag_drop.js before this script

function before_add_element(element, index) {
    //Write script that will run before add ellement to table
    label = element.getElementsByClassName("label");
    if (label.length !== 0){
        labelItem = label.item(0);
        labelItem.innerHTML = element.getAttribute("labelstring") + index;
    }
}

function is_forbidden_to_chage(dataset, data) {
    elAtype = dataset.atype;
    moveAtype = data[2];
    if (moveAtype !== elAtype || elAtype === "G" || moveAtype === "G"){
        return true
    }
    return false
}

function set_event_data_transfer_from_event_target_dataset(event_data_transfer, event_target_dataset) {
    // Function that work with event.dataTransfer and event_target_dataset. Example:
    //  event.dataTransfer.setData("text/plain", event.target.dataset.index + ',' + event.target.dataset.move_url);
    event_data_transfer.setData("text/plain", event_target_dataset.index + ',' + event_target_dataset.move_url + ',' + event_target_dataset.atype);
}
