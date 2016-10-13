$(document).ready(function(){
    console.log('Every Problem Script working');

    var problemID;
    
    $('button.submit').off('.hx').one('click.hx tap.hx', function(event){
        problemID = $(this).closest('.xblock').attr('data-usage-id');
        onCheckButton(problemID);
    });

    function afterButtonPress(problemID){
        
        // Add new listener to the submit button.
        var theButton = $('div.xblock[data-usage-id="' + problemID + '"]').find('button.submit');
        theButton.off('.hx').on('click.hx tap.hx', function(problemID){
            problemID = $(this).closest('.xblock').attr('data-usage-id');
            onCheckButton(problemID);
        });
        
        // Let the system know the grade.
        // We're reading it straight off the page.
        // Sure wish we had a better way to do this.
        var gradeNumber = 0;
        var maxGradeNumber = 0;
        
        var gradeFullText = $('div.xblock[data-usage-id="' + problemID + '"]').find('.problem-progress').text();
        var gradeText = gradeFullText.split(' ')[0];
        
        if(gradeText.length > 1){
            gradeNumber = gradeText.split('/')[0];
            maxGradeNumber = gradeText.split('/')[1];
        }else{
            maxGradeNumber = gradeText;
        }

        // Get username after button press, since analytics variable not available right away at document.ready
        var username = analytics._user._getTraits()['username'];
        
        //Log info: edX username, problem ID, current and maximum grade.
        console.log('User: ' + username);
        console.log('Problem ID: ' + problemID);
        console.log('Current grade: ' + gradeNumber);
        console.log('Max grade: ' + maxGradeNumber);

        // Make POST request with grade info
        $.post("https://adaptive-edx.vpal.io/api/problem_attempt", {
                user: username,
                problem: problemID,
                points: gradeNumber,
                max_points: maxGradeNumber
            }
            ,function(data){console.log("Made POST request: "+ data.message);},"json"
        );

    }

    function onCheckButton(problemID){
        
        // Wait before rebinding the listeners and getting the log info.
        setTimeout(afterButtonPress.bind(null, problemID), 2000);
    }

});