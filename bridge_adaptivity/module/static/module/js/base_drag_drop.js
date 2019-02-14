// Utility function which exchange element's index
function updateElement(element, index) {
    element.dataset.index = index;
    return element;
}


function before_add_element(element) {
    // Write a script that will be run before adding an ellement to the table
}

function after_add_elements() {
    // Write a script that will be run after adding all ellements to the table
}

function is_forbidden_to_chage(dataset, data) {
    return false
}

function get_ordering_elements_list(moveIndex, elIndex) {
    let collectionList = $('tr.droppable'),
        shift = 0,
        newCollectionList = [];
    $.each(collectionList, function (index, _) {
            if (index == elIndex) {
                newCollectionList[index] = updateElement(collectionList[moveIndex], index);
                shift = moveIndex < elIndex ? 0 : -1;
            } else if (index == moveIndex && moveIndex < elIndex) {
                shift = 1;
                newCollectionList[index] = updateElement(collectionList[index + shift], index);
            } else if (index == moveIndex && moveIndex > elIndex) {
                newCollectionList[index] = updateElement(collectionList[index + shift], index);
                shift = 0;
            } else {
                newCollectionList[index] = updateElement(collectionList[index + shift], index);
            }
        });
    return newCollectionList
}

function change_move_url(moveUrl, element_dataset) {
    // Change move url
    elIndex = parseInt(element_dataset.index);
    return moveUrl.replace("?", elIndex + "?");
}

// Function processing drop of the element
function drop_handler(event, el) {
    event.preventDefault();
    let data = event.dataTransfer.getData("text/plain").split(','),
        elIndex = parseInt(el.dataset.index), // index of the target element
        moveUrl = data[1], // move URL of the dropped element
        moveIndex = parseInt(data[0]), // initial index of the dropped element
    is_forbidden_extra_cheack = is_forbidden_to_chage(el.dataset, data);
    if (moveIndex === elIndex || is_forbidden_extra_cheack) {
        console.log("Item doesn't change the order");
    } else {
        console.log("Trying change Item " + moveIndex + " order to " + elIndex);
        moveUrl = change_move_url(moveUrl, el.dataset)
        orderingElementsList = get_ordering_elements_list(moveIndex, elIndex);
        $.each(orderingElementsList, function (index, element) {
            before_add_element(element, index);
            $("table").append(element);
        });
        after_add_elements();
        $.ajax({
            type: "GET",
            url: moveUrl,
            success: responseData => {
                console.log("Collection's changed order is persisted to the backend.");
            },
            error: responseData => console.log("Cannot change collections order " + responseData)
        });
    }
}

function dragover_handler(event, drop_effect="move") {
    event.preventDefault();
    // Set the dropEffect to move
    event.dataTransfer.dropEffect = drop_effect;
}


function set_event_data_transfer_from_event_target_dataset(event_data_transfer, event_target_dataset) {
    // Function that work with event.dataTransfer and event_target_dataset. Example:
    // event_data_transfer.setData("text/plain", event_target_dataset.index + ',' + event_target_dataset.move_url);
}

// Handler function of the drag start process
function dragstart_handler(event, drop_effect="move") {
    set_event_data_transfer_from_event_target_dataset(event.dataTransfer, event.target.dataset)
    event.dropEffect = drop_effect;
}
