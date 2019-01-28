$(function () {
    const buttons = $('.preview-assessment-buttons');
    const assessmentContent = $('#assessment-content');
    $('.preview-assessment-back-btn').click((e) => {
        window.location = e.currentTarget.value;
    });
    if (buttons.length === 0) return;

    const toogleTask = button => {
        buttons.removeClass('btn-primary');
        button.addClass('btn-primary');
        assessmentContent[0].contentWindow.location.replace(button.data().previewUrl);
    };

    buttons.on("click", ev => toogleTask($(ev.target)));
    toogleTask($(buttons[0]))

}).call(this);
