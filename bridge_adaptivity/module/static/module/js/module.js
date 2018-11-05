(function ($) {
    "use strict";

    $(function () {
        var defaultSourceItemTitle = "No Title";
        var $filter = $("#filter"),
            filterVal,
            regexFilter;

        $filter.change(function () {
            filterVal = $("#filter").val();
            if (filterVal) {
                regexFilter = new RegExp(filterVal, "i");
            } else {
                regexFilter = null;
            }
            var courseData = bridgeState.accordion.courseData[bridgeState.accordion.opened];
            var content_panel = $("#content-panel-" + bridgeState.accordion.opened + " div.panel-body");
            renderCourseBlocks(courseData, content_panel);

        });
        var modalContentFrame = $("#modal-source-preview");
        var activitiesData = $.map($(".activity"), function(activityRow) {
            var $activityRow = $(activityRow);
            return {
                id: $activityRow.data("id"),
                sourceActive: $activityRow.data("sourceActive"),
                name: $activityRow.data("activity-name"),
                content_source_id: $activityRow.data('content_source_id'),
                launch_url: $activityRow.data("activity-source-launch-url")
            };
        });

        function typeToIcon(itemType) {
            switch (itemType) {
                case "html":
                    return "glyphicon-list-alt";
                case "problem":
                    return "glyphicon-question-sign";
                case "video":
                    return "glyphicon-facetime-video";
                default:
                    return "glyphicon-option-horizontal";
            }
        }

        var bridgeStateLoad = function() {
            var storageState = JSON.parse(sessionStorage.getItem("bridgeState"));
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
                if (this.accordion.opened != null){
                    $("#accordion a[data-course-index='" + this.accordion.opened + "']").trigger("click");
                    // no need to pass content_source_id, because it will be loaded from sessionStorage with data
                    clickHandler(this.accordion.opened, this.accordion.activeCourseId, this, null);
                }
            }
            console.log("State loaded: ", this);
        };

        var bridgeState = (function() {
            return {
                load: bridgeStateLoad,
                save: function() {
                    sessionStorage.setItem("bridgeState", JSON.stringify(this));
                    console.debug("State saved: ", this);
                }
            };
        }());

        bridgeState.load();

        // activity source preview:
        $.each(activitiesData, function (i, activity) {
            createPreviewButton(
                activity["name"],
                activity["launch_url"],
                activity,
                $("#activity-row-" + i + " td div").last(),
                modalContentFrame
            );
        });

        $("#accordion").find("a[data-course-id]").on("click", function () {
            var target = $(this);
            var activeCourseIndex = target.data("course-index");
            var activeCourseId = target.data("course-id");
            var activeCourseContentSourceId = target.data("content_source_id");

            if (activeCourseIndex !== bridgeState.accordion.opened) {
                bridgeState.accordion.opened = activeCourseIndex;
                bridgeState.save();
                clickHandler(activeCourseIndex, activeCourseId, bridgeState, activeCourseContentSourceId);
            } else {
                bridgeState.accordion.opened = null;
                bridgeState.save();
            }
        });

        function clickHandler(activeCourseIndex, activeCourseId, state, contentSourceId) {
            var courseData;
            var content_panel = $("#content-panel-" + activeCourseIndex + " div.panel-body");
            if (state.accordion.courseData[activeCourseIndex] !== undefined) {
                console.log("Taking data from cache ...");
                courseData = state.accordion.courseData[activeCourseIndex];
                renderCourseBlocks(courseData, content_panel);
            } else {
                var requestData = {
                    course_id: activeCourseId,
                    content_source_id: contentSourceId
                };
                $.ajax({
                    type: "POST",
                    url: internalUrls.apiSources,
                    data: requestData,
                    success: responseData => {
                        console.log("Processing API request...");
                        state.accordion.courseData[activeCourseIndex] = responseData;
                        state.accordion.activeCourseId = activeCourseId;
                        state.save();
                        renderCourseBlocks(responseData, content_panel);
                    },
                    error: responseData => console.log("Can load source info " + responseData)
                });
            }
        }

        function getActivityCreationUrl(item) {
            const activityAddUrlHolder =  $('#activity-add-url-holder');
            // Note(braiko) this method called when state from session storage loaded,
            // but there no activities on this page.
            if(activityAddUrlHolder.length == 0)
            {
                return "";
            }
            return `${$('#activity-add-url-holder').data().url}?`
                + `name=${item["display_name"]}&`
                + `source_name=${item["display_name"]}&`
                + `source_launch_url=${item["lti_url"]}&`
                + `lti_consumer=${item["content_source_id"]}&`
                + `stype=${item["type"]}`;
        }

        function renderCourseBlocks(courseData, container) {
            console.log("Rendering course...");
            const usedLtiUrls = $.map(activitiesData, function(data) { return data.launch_url });
            let sourcesList = $("<div/>").addClass("list-group");
            if (courseData.length === 0) {
                console.log("Course is empty! No activities were found.");
                $(
                    "<span class='list-group-item unreachable-activity'>" +
                    "The course is empty, no activities were found!</span>"
                ).appendTo(sourcesList);
            } else {
                $.each(courseData, function (i, item) {
                    var listItem = $("<button class='list-group-item' type='button' />").appendTo(sourcesList);
                    $(
                        `<span data-toggle='type' title="${item.type}" ` +
                        `class="badge pull-left glyphicon ${typeToIcon(item.type)} style:'margin-right"> </span>`
                    ).appendTo(listItem);

                    var sourceButton = $("<span/>");
                    // if item already is used by some Activity => block and highlight:

                    if (item['visible_to_staff_only']) {
                        listItem.addClass("unreachable-activity");
                    }

                    if (usedLtiUrls.indexOf(item["lti_url"]) !== -1) {
                        sourceButton.css("text-decoration", "line-through").addClass("bg-info");
                    } else {
                        if (item['visible_to_staff_only']) {
                            listItem.click(() => {
                                let modal = $("#not-available-for-student")
                                modal.find('.add-new-activity').attr('value', getActivityCreationUrl(item))
                            modal.modal("show")
                        })
                        } else {
                            listItem.attr("value", getActivityCreationUrl(item)).click(modal_form_launcher);
                        }
                    }
                    // if title is empty => set default title:
                    if (!item["display_name"].length) {
                        sourceButton.text(defaultSourceItemTitle);
                    } else {
                        sourceButton.text(item["display_name"]);
                    }
                    if (regexFilter) {
                        if (!regexFilter.exec(sourceButton.text())) {
                            listItem.remove();
                        }
                    }
                    sourceButton.appendTo(listItem);
                    // Cource block preview:
                    createPreviewButton(item["display_name"], item["lti_url"], item, listItem, modalContentFrame);
                });
            }
            container.html(sourcesList);
        }

        function createPreviewButton(title, ltiUrl, activity, parent, modalFrame) {
            var contentSourceId = activity['content_source_id'];
            var sourceId = activity['id'];

            var preview = $("<a/>")
                .addClass("pull-right")
                .attr("data-toggle", "modal")
                .attr("data-target", "#sourceModal")
                .appendTo(parent);
            var previewButton = $("<button/>", {"class": "btn btn-default btn-sm"})
                .appendTo(preview);
            $("<span/>")
                .addClass("glyphicon glyphicon-eye-open")
                .attr("data-display-name", title)
                .attr("data-lti-url", ltiUrl)
                .appendTo(previewButton);
            previewButton.on("click", function (e) {
                e.stopImmediatePropagation();
                $("#sourceModal").modal("show");
                $("#sourceModalLabel").text(title);
                configurePreview(title, ltiUrl, sourceId, contentSourceId, modalFrame);
            });
        }

        function configurePreview(title, ltiUrl, sourceId, contentSourceId, modalFrame) {
            var idParam = "source_id=" + sourceId + "&";
            var displayNameParam = "source_name=" + title + "&";
            var ltiUrlParam = "source_lti_url=" + ltiUrl + "&";
            var contentSourceIdParam = "content_source_id=" + contentSourceId + "&";
            var previewUrl = (
                internalUrls.ltiSourcePreview + "?" + idParam + displayNameParam + ltiUrlParam + contentSourceIdParam
            );
            modalFrame
                .attr("src", previewUrl)
                .attr("title", title)
                .attr("name", sourceId);
        }

        // Launch URL fetching:
        const launchUrlFetcher = new Clipboard(
            '#launch-url-fetcher',
            {
                text: trigger => {
                    return trigger.getAttribute('data-clipboard-text').replace('set_me_unique', (new Date().getTime()))
                }
            });
        launchUrlFetcher.on("success",  function (e) {
            var button = $(e.trigger).find(".btn");
            button.addClass("btn-success");
            setTimeout(function() {
                button.removeClass("btn-success");
            }, 2000);
        });

        var engineFailure = $("#activities").data("engine");
        if (engineFailure){
            console.log("Adaptive Engine failure to proceed!");
            $("#engineFailureModal").modal("show");
        }

        // jQuery plugin to prevent double submission of forms
        jQuery.fn.preventDoubleSubmission = function () {
            $(this).on('submit', function (e) {
                var $form = $(this);

                if ($form.data('submitted') === true) {
                    // Previously submitted - don't submit again
                    e.preventDefault();
                } else {
                    // Mark it so that the next submit can be ignored
                    $form.data('submitted', true);
                }
            });

            // Keep chainability
            return this;
        };

        var getDataForWarning = function (elem) {
            $elem = $(elem);
            return $elem.closest('a').data();
        };

        $(".show-warning,.show-alarm,.delete-object button").on('click', function(e){
            var data = getDataForWarning(this);
            if(data && data.id) {
                $("#deleteModal" + data.id).modal('show');
            } else {
                $("#deleteModal").modal('show');
            }
            e.stopPropagation();
            e.preventDefault();

        });

        $('form').preventDoubleSubmission();



        $('#link-objects-modal').on('click', function(e){
            $('#sourceModal').modal('show');
        });

        $("#link-objects").on("click", function(e) {
            var $form = $("#link-objects-form");
            var url = $form.attr('action');
            var data = $form.serialize();
            $.post(url, data, function(data){
                if(data.success) {
                    window.location.href = data['url'];
                } else {
                    $form.html(data.html);
                };
            },
            'json');
        });

         $('#launch_url_help').tooltip({
             title: "<b>copy launch URL</b> button generates unique LTI Launch URL to the chosen collection. " +
             "To add the same collection in the one course please use dissimilar URLs for each collection entrance. ",
             html: true

         });

         $('#demo_help').tooltip({
             title: "<b>Demo adaptivity</b> shows the adaptivity behavior for the provided answers",
             html: true

         });

        function patchModalForm(modal, url = undefined) {
            const form = modal.find('form');
            url = url || form[0].action;
            form.submit(function (e) {
                $.ajax({
                    type: form[0].method,
                    url: url,
                    data: form.serialize(),
                    success: modalSuccessListener(url),
                });
                e.preventDefault();
                return false;
            });
        }

        const modalSuccessListener = (url) => {
            return result => {
                let modal = $('#modal-wrapper');
                if (result.status !== undefined && result.status === 'ok') {
                    window.location.href = window.location.href ;
                    return;
                }
                modal.find('.modal-body').html(result);
                let title = modal.find('.modal-body').find('#title');
                modal.find('.modal-title').text(title.length > 0 ? title.data().title : '');
                patchModalForm(modal, url);
                modal.modal('show')
            }
        };

        function modal_form_launcher(e){
            const url = $(e.currentTarget).attr('value');
            // NOTE: fix for handling event from the parent or child items
            if (url === undefined) {
                console.log("Can not display modal window with undefined url");
                return true;
            }

            $.ajax({
                    type: "GET",
                    url: url,
                    success: modalSuccessListener(url)
                }
            );
        }

        $('.modal_launcher').click(modal_form_launcher);

        $('#collection-preview-button').click(e => {
            if($('.activity').length === 0) {
                $('#preview-warning').modal('show');
                e.preventDefault();
                return true;
            }
        });

        window.onbeforeunload = () => {
            if(performance.navigation.type === PerformanceNavigation.TYPE_RELOAD)
                sessionStorage.clear();
        }
    });
}(jQuery));
