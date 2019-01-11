// Utility function which exchange element's index
function updateElement(element, index) {
    element.dataset.index = index;
    return element;
}

// Function processing drop of the element
function drop_handler(event, el) {
    event.preventDefault();
    let data = event.dataTransfer.getData("text/plain").split(','),
        elIndex = el.dataset.index, // index of the target element
        elAtype = el.dataset.atype, // atype of the target element
        moveUrl = data[1], // move URL of the dropped element
        moveIndex = data[0], // initial index of the dropped element
        moveAtype = data[2]; // atype of the dropped element
    if (moveIndex === elIndex || moveAtype !== elAtype || elAtype === "G" || moveAtype === "G" ) {
        console.log("Item doesn't change the order");
    } else {
        console.log("Trying change Item " + moveIndex + " order to " + elIndex);
        moveUrl = moveUrl.replace("?", elIndex + "?");
        let collectionList = $('tr.droppable'),
            shift = 0,
            newCollectionList = [];
        // Update elements order on the frontend
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
        collectionList.remove();
        $.each(newCollectionList, function (index, element) {
            $("table").append(element);
        });
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

// Handler function of the drag over process
function dragover_handler(event) {
    event.preventDefault();
    // Set the dropEffect to move
    event.dataTransfer.dropEffect = "move";
}

// Handler function of the drag start process
function dragstart_handler(event) {
    event.dataTransfer.setData("text/plain", event.target.dataset.index + ',' + event.target.dataset.move_url + ',' + event.target.dataset.atype);
    event.dropEffect = "move";
}
