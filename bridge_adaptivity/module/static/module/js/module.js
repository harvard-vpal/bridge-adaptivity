(function ($) {
    $(document).ready(function () {
        var typeToIcon = {
            html: "glyphicon-list-alt",
            problem: "glyphicon-question-sign",
            video: "glyphicon-facetime-video",
            other: "glyphicon-option-horizontal"
        };
        var bridgeState = (function() {
            return {
                load: function() {
                    var storageState = JSON.parse(localStorage.getItem('bridgeState'));
                    if (storageState === null) {
                        $.extend(this, {
                            accordion: {
                                opened: null,
                                activeCourseId: null,
                                courseData: {}
                            }
                        });
                        console.log("State initialization...");
                    } else {
                        $.extend(this, storageState);
                        console.log("State from storage...");
                        $("#accordion a[data-course-index='" + this.accordion.opened + "']").trigger('click');
                        clickHandler(this.accordion.opened, this.accordion.activeCourseId, this);
                    }
                    console.log("State loaded: ", this);
                },

                save: function() {
                    localStorage.setItem('bridgeState', JSON.stringify(this));
                    console.debug("State saved: ", this);
                }
            };
        }());

        bridgeState.load();

        var modalContentFrame = $('#modal-source-preview');

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

            if (activeCourseIndex !== bridgeState.accordion.opened) {
                bridgeState.accordion.opened = activeCourseIndex;
                bridgeState.save();
                clickHandler(activeCourseIndex, activeCourseId, bridgeState);
            } else {
                bridgeState.accordion.opened = null;
                bridgeState.save();
            }
        });

        function clickHandler(activeCourseIndex, activeCourseId, state) {
            var courseData;
            var content_panel = $("#content-panel-" + activeCourseIndex + " div.panel-body");
            if (state.accordion.courseData[activeCourseIndex] !== undefined) {
                console.log("Taking data from cache ...");
                courseData= state.accordion.courseData[activeCourseIndex];
                renderCourseBlocks(courseData, content_panel);
            } else {
                var requestData = {course_id: activeCourseId};
                $.post(internalUrls.apiSources, requestData, function (responseData) {
                    console.log("Processing API request...");
                    state.accordion.courseData[activeCourseIndex] = responseData;
                    state.accordion.activeCourseId = activeCourseId;
                    state.save();
                    renderCourseBlocks(responseData, content_panel);
                });
            }
        }

        function renderCourseBlocks(courseData, container) {
            console.log("Rendering course...");
            var usedLtiUrls = activitiesData.map(function(currentValue) {
                return currentValue['source_launch_url']
            });
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
                var sourceButton = $('<span/>');
                if (usedLtiUrls.indexOf(item['lti_url']) !== -1) {
                    sourceButton
                        .addClass('bg-info');
                } else {
                    sourceButton
                        .attr('data-toggle', 'modal')
                        .attr('data-target', '#activityModal');
                }
                sourceButton
                    .text(item['display_name'])
                    .appendTo(listItem)
                    .on('click', function () {
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
