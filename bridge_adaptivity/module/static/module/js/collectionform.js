
var update_collection_form = function() {
    var clFormUrl = $("#link-objects-form-update").data("collection_url");
    var cl = $("select[name='collection_group-collection'] option:selected").val();
    console.log(clFormUrl);
    $.get(clFormUrl, {
        collection_id: cl,
      }, function(response) {
        console.log(response);
        $("div.collection_form").html(response);
    })
};


$(document).ready(function() {

    $("form select[name=collection_group-collection]").on("change", function() {
      update_collection_form();
    });
});