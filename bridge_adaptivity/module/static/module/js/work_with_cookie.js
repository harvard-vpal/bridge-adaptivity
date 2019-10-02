function getCookie(name) {
    // Get the value of cookie by name
    // I used a group with name as value in `name` parameter.
    let v = document.cookie.match('[^|;] ?'+name+'=(?<'+name+'>[^;]*)[;|$]?');
    return v ? v.groups[name] : null;
}

function setCookie(name, value, minutes) {
    // Set the new cookie and add expires Date
    let d = new Date;
    d.setTime(d.getTime() + 60 * 1000 * minutes);
    document.cookie = name + "=" + value + ";path=/;expires=" + d.toGMTString();
}

function deleteCookie(name) {
    // Delete cookie by set negative expires date and empty value
    setCookie(name, '', -1);
}
