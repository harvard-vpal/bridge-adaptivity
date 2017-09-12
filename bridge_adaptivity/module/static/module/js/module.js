(function ($) {
    $(document).ready(function () {
        var bridgeState = (function() {
            return {
                load: function() {
                    var state = JSON.parse(localStorage.getItem('bridgeState'));
                    if (state == null) {
                        state = {
                            accordion: {
                                opened: null,
                                courseData: {}
                            }
                        };
                        console.log("State initialization: ", state.accordion);
                    } else {
                        console.log("State from storage: ", state.accordion);
                        // var $a = $("#accordion")
                        //     .find($("#accordion a[data-course-index='" + state.accordion.opened + "']"))
                        //     .trigger('click');
                        // console.log("Found: ", $a[0])
                    }
                    $.extend(this, state);
                    console.log("State loaded: ", this);
                },

                save: function(newState) {
                    var state = {};
                    $.extend(state, newState);
                    localStorage.setItem('bridgeState', JSON.stringify(state));
                    console.log("State saved: ", state);
                }
            };
        }());

        bridgeState.load();

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
            var activeCourseIndex = target.data('course-index');
            var activeCourseId = target.data("course-id");
            clickHandler(activeCourseIndex, activeCourseId, bridgeState);
        });

        function clickHandler(activeCourseIndex, activeCourseId, state) {
            var courseData;
            var content_panel = $("#content-panel-" + activeCourseIndex).find(".panel-body").first();
            if (content_panel.find('ul.content-sources').length) {
                return
            }

            if (state.accordion.courseData[activeCourseIndex] !== undefined) {
                courseData= state.accordion.courseData[activeCourseIndex];
                renderCourseBlocks(courseData, content_panel);
            } else {
                var requestData = {course_id: activeCourseId};
                $.post(internalUrls.apiSources, requestData, function (responseData) {
                    console.log("API request...");
                    // bridgeState.save({
                    //     accordion: {
                    //         opened: (activeCourseIndex != bridgeState.accordion.opened) ? activeCourseIndex : null,
                    //         courseData: {}
                    //     }.courseData[activeCourseIndex] = responseData
                    // });
                    renderCourseBlocks(responseData, content_panel);
                });
            }
        }

        function renderCourseBlocks(courseData, container) {
            var sourcesList = $('<div/>').addClass('list-group');
            $.each(courseData, function (i, item) {
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
            container.append(sourcesList);
        }

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
