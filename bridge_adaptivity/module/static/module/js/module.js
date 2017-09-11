(function ($) {
    $(document).ready(function () {
        var modalContentFrame = $('#modal-source-preview');
        var typeToIcon = {
            html: "glyphicon-list-alt",
            problem: "glyphicon-question-sign",
            video: "glyphicon-facetime-video",
            other: "glyphicon-option-horizontal"
        };

        // activity source preview:
        $.each(activitiesData, function (i, activity) {
            createPreviewButton(
                activity['name'],
                activity['source_launch_url'],
                activity['id'],
                $('#activity-row-' + i + ' td').last(),
                modalContentFrame
            )
        });

        $("#accordion").find("a[data-course-id]").on('click', function () {
            var target = $(this);
            var data = {course_id: target.data("course-id")};
            $.post(internalUrls.apiSources, data, function (data) {
                var content_panel = target.closest(".panel.panel-default").find(".panel-body").first();
                if (content_panel.find('ul.content-sources').length) {
                    return
                }

                var sourcesList = $('<div/>').addClass('list-group');
                $.each(data, function (i, item) {
                    var listItem = $('<button/>')
                        .addClass('list-group-item')
                        .attr('type', 'button')
                        .appendTo(sourcesList);
                    var sourceIcon = $('<span/>')
                        .data('toggle', 'tooltip')
                        .attr('title', item.type)
                        .addClass("badge pull-left glyphicon " + typeToIcon[item.type])
                        .text(" ")
                        .css('margin-right', '5px')
                        .appendTo(listItem);
                    var sourceButton = $('<span/>')
                        .attr('data-toggle', 'modal')
                        .attr('data-target', '#activityModal')
                        .text(item['display_name'])
                        .appendTo(listItem);
                    sourceButton.on('click', function () {
                        setInitialActivityData(item);
                    });
                    createPreviewButton(
                        item['display_name'],
                        item['lti_url'],
                        item['id'],
                        listItem,
                        modalContentFrame
                    )
                });
                content_panel.append(sourcesList);
            });
        });

        function createPreviewButton(title, ltiUrl, sourceId, parent, modalFrame) {
            var preview = $('<a/>')
                .addClass("pull-right")
                .attr('data-toggle', 'modal')
                .attr('data-target', '#sourceModal')
                .appendTo(parent);
            var previewButton = $('<button/>', {'class': 'btn btn-default btn-sm'})
                .appendTo(preview);
            var previewButtonBody = $('<span/>')
                .addClass("glyphicon glyphicon-eye-open")
                .attr('data-display-name', title)
                .attr('data-lti-url', ltiUrl)
                .appendTo(previewButton);
            previewButton.on('click', function () {
                $('#sourceModalLabel').text(title);
                configurePreview(modalFrame, title, ltiUrl, sourceId);
            })
        }

        function configurePreview(frame, title, ltiUrl, sourceId) {
            var idParam = "source_id=" + sourceId + "&";
            var displayNameParam = "source_name=" + title + "&";
            var ltiUrlParam = "source_lti_url=" + ltiUrl + "&";
            var previewUrl = internalUrls.ltiSourcePreview + "?" + idParam + displayNameParam + ltiUrlParam;
            frame
                .attr('src', previewUrl)
                .attr('title', title)
                .attr('name', sourceId);
        }

        function setInitialActivityData(source) {
            // prepopulate Activity creation modal form:
            $('#id_name').val(source['display_name']);
            $('#id_source_name').val(source['display_name']);
            $('#id_source_launch_url').val(source['lti_url']);
            $('#id_source_context_id').val(source['context_id']);
        }
    });
}(jQuery));
