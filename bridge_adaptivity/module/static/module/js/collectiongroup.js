// var update_form = function() {
//     var gpFormUrl = $("#group_form").data("policy_url");
//     var gp = $("select[name='group-grading_policy_name'] option:selected").val();
//     console.log(gp);
//     $.get(gpFormUrl, {
//         grading_policy: gp,
//       }, function(response) {
//         $("div.grading_policy").html(response);
//     })
// };
//
// var popover_policy = function(){
//     $('#policy_help[data-toggle="popover"]').popover({
//         title: function(){
//             return $('.policy_select option:selected').data().summary;
//         },
//         content: function(){
//             return $('.policy_select option:selected').data().detail;
//         },
//         trigger: 'hover'
//     });
// };
//
// $(document).ready(function() {
//     update_form();
//     // when page is loaded - we should be ready to show policy popover
//     popover_policy();
//
//     $("form select[name=group-grading_policy_name]").on("change", function() {
//       update_form();
//       // when form changed - update policy popover
//       popover_policy();
//     });
// });

//-----


var update_form = function() {
    var gpFormUrl = $("#link-objects-form").data("policy_url");
    var gp = $("select[name='grading_policy_name'] option:selected").val();
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
    update_form();
    // when page is loaded - we should be ready to show policy popover
    popover_policy();

    $("form select[name=grading_policy_name]").on("change", function() {
      update_form();
      // when form changed - update policy popover
      popover_policy();
    });
});


