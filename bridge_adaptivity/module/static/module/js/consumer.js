$(document).ready(function() {

    $("#contributors .delete-contributor").on("click", function() {
            var element = $(this);
           $.ajax({
              url: this.dataset["remove_url"],
            }).done(function() {
              element.closest("tr").remove();
            });
    });
});
