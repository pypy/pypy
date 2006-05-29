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

function alloc_and_set(L0, len, elem) {
    l = [];
    for(i = 0; i < len; ++i){
        l[i] = elem;
    }
    return(l);
}

function strconcat(s1, s2) {
    return(s1+s2);
}

function stritem(cl, s, it) {
    return(s[it]);
}

function delitem(fn, l, i) {
    for(j = i; j < l.length-1; ++j) {
        l[j] = l[j+1];
    }
    l.length--;
}

function strcmp(s1, s2) {
    if ( s1 < s2 ) {
        return ( -1 );
    } else if ( s1 == s2 ) {
        return ( 0 );
    }
    return (1);
}

function startswith(s1, s2) {
    if (s1.length<s2.length) {
        return(false);
    }
    for (i = 0; i < s2.length; ++i){
        if (s1[i]!=s2[i]) {
            return(false);
        }
    }
    return(true);
}

function endswith(s1, s2) {
    if (s2.length>s1.length) {
        return(false);
    }
    for (i = s1.length-s2.length; i<s1.length; ++i) {
        if (s1[i]!=s2[i-s1.length+s2.length]) {
            return(false);
        }
    }
    return(true);
}
