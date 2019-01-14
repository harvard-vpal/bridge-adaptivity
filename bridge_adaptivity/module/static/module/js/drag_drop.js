// include base_drag_drop.js before this script

function set_event_data_transfer_from_event_target_dataset(event_data_transfer, event_target_dataset) {
    // Function that work with event.dataTransfer and event_target_dataset. Example:
    //  event_data_transfer.setData("text/plain", event_target_dataset.index + ',' + event_target_dataset.move_url);
    event_data_transfer.setData("text/plain", event_target_dataset.index + ',' + event_target_dataset.move_url)
}
