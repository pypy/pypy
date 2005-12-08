var in_browser;
try {
    dummy = alert;
    in_browser = true;
} catch (e) {
    in_browser = false;
}

function log(s) {
    if (in_browser) {
        var logdiv = document.getElementById('logdiv');
        logdiv.innerHTML = new Date().getTime() + ': ' + s + "<br/>" + logdiv.innerHTML;
    } else {
        print('log: ' + s);
    }
}
