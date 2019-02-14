
var update_form = function() {
    var gpFormUrl = $("#link-objects-form-update").data("policy_url");
    var gp = $("select[name='collection_group-grading_policy_name'] option:selected").val();
    console.log(gp);
    $.get(gpFormUrl, {
        grading_policy: gp,
      }, function(response) {
        $("div.grading_policy").html(response);
    })
};

var popover_policy = function(){
    $('#policy_help[data-toggle="popover"]').popover({
        title: function(){
            return $('.policy_select option:selected').data().summary;
        },
        content: function(){
            return $('.policy_select option:selected').data().detail;
        },
        trigger: 'hover'
    });
};

$(document).ready(function() {
    if( ! $("div.grading_policy .form-group").hasClass( "has-error") ){
        update_form();
        // when page is loaded - we should be ready to show policy popover
        popover_policy();
    }

    $("form select[name=collection_group-grading_policy_name]").on("change", function() {
      update_form();
      // when form changed - update policy popover
      popover_policy();
    });
});


