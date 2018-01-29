var update_form = function() {
    var gp = $('select[name="group-grading_policy_name"]').val();
    console.log(gp);
    $.get("{% url 'module:grading_policy_form' group_slug=group.slug %}", {
        grading_policy: gp,
        csrfmiddlewaretoken: '{{ csrf_token }}',
      }, function(response) {
         $("div.grading_policy").html(response);
      })
};
$(document).ready(function() {
    $('form select[name=group-grading_policy_name]').on('change', function() {
      update_form();
    });
})
