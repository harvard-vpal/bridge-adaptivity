var update_form = function() {
    var gpFormUrl = $("#group_form").data("policy_url");
    console.log(gpFormUrl);
    var gp = $("select[name='group-grading_policy_name']").val();
    console.log(gp);
    $.get(gpFormUrl, {
        grading_policy: gp,
        csrfmiddlewaretoken: "{{ csrf_token }}",
      }, function(response) {
        $("div.grading_policy").html(response);
    })
};
$(document).ready(function() {
    update_form();

    $("form select[name=group-grading_policy_name]").on("change", function() {
      update_form();
    });
});
