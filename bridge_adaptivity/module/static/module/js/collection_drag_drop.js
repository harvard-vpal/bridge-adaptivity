// WARNING(AndreyLykhoman):include base_drag_drop.js before this script

before_add_element = function() {
    // Write a script that will be run before adding an ellement to the table
    // NOTE(AndreyLykhoman): Checking atype of elements and increase index or starting from zero
    atype = '';
    index = 0;
    return function (element) {
        label = element.getElementsByClassName("label");
        if (label.length !== 0) {
            labelstring = element.getAttribute("data-atype");
            if (atype !== labelstring) {
                atype = labelstring;
                index = 0;
            } else {
                index++;
            }
            // NOTE(AndreyLykhoman): Setting up a right index to 'data-index' attribute in the element. It's needed for
            //  correct working drag-and-drop in the next usage.
            element.dataset.index = index;
            labelItem = label.item(0);
            labelItem.innerHTML = element.getAttribute("labelstring") + index;
        }
    }
}();

function is_forbidden_to_chage(dataset, data) {
    elAtype = dataset.atype;
    moveAtype = data[2];
    if (moveAtype !== elAtype || elAtype === "G" || moveAtype === "G") {
        return true
    }
    return false
}

function set_event_data_transfer_from_event_target_dataset(event_data_transfer, event_target_dataset) {
    // Function that work with event.dataTransfer and event_target_dataset. Example:
    // event_data_transfer.setData("text/plain", event_target_dataset.index + ',' + event_target_dataset.move_url);
    event_data_transfer.setData("text/plain", event_target_dataset.index + ',' + event_target_dataset.move_url + ',' + event_target_dataset.atype);
}
