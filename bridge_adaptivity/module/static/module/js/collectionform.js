
var update_collection_form = function() {
    var collectionFormUrl = $("#link-objects-form-update").data("collection_url");
    var collection_id = $("select[name='collection_group-collection'] option:selected").val();
    $.get(collectionFormUrl, {
        collection_id: collection_id,
      }, function(response) {
        $("div.collection_form").html(response);
    })
};


$(document).ready(function() {

    $("form select[name=collection_group-collection]").on("change", function() {
      update_collection_form();
    });
});
