(function(){
    var forbidNext = $("#next-button").data("forbidden");
    if (forbidNext){
        console.log("Current Activity is not answered, NEXT is forbidden!");
        $("#forbidNextModal").modal("show");
    };
}());
