$(document).ready(function() {
    $("#contributors .delete-contributor").on("click", function() {
        var element = $(this);
        $.ajax({
            url: this.dataset["remove_url"],
        }).done(function() {
            element.closest("tr").remove();
        }).fail(function (jqXHR, textStatus, errorThrown) {
            console.log(textStatus + "(" + errorThrown + "): " + jqXHR.responseText.split('\n')[0]);
            element.closest("tr").children("td.error").append(
                "<p>Cannot be removed, please try again later. " +
                "If the problem will be procced contact with the Bridge admin.</p>"
            );
        });
    });
});
