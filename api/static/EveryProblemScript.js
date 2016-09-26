$(document).ready(function(){
    console.log('Every Problem Script working');

    var problemID;
    
    $('button.check').off('.hx').one('click.hx tap.hx', function(){
        problemID = $(this).closest('.xblock').attr('data-usage-id');
        onCheckButton(problemID);
    });

    function afterButtonPress(problemID){
        
        // Add new listener to the check button.
        var theButton = $('div.xblock[data-usage-id="' + problemID + '"]').find('button.check');
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
        var gradeText = gradeFullText.split('/');
        
        if(gradeText.length > 1){
            gradeNumber = gradeText[0].split('(')[1];
            maxGradeNumber = gradeText[1].split(' ')[0];
        }else{
            maxGradeNumber = gradeText[0].split(' ')[0].split('(')[1];
        }

        // Get username 
        var username;
        username = analytics._user._getTraits()['username'];
        // If analytics user info is empty, grab from browser cookie
        if (!username){
            username = JSON.parse(eval(getCookie('prod-edx-user-info')))['username'];
        }

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

    function getCookie(cname){
        // get a value of a browser cookie
        var name = cname + "=";
        var ca = document.cookie.split(';');
        for(var i = 0; i <ca.length; i++) {
            var c = ca[i];
            while (c.charAt(0)==' ') {
                c = c.substring(1);
            }
            if (c.indexOf(name) == 0) {
                return c.substring(name.length,c.length);
            }
        }
        return "";
    }

});
