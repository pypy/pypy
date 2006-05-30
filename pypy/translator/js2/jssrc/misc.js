Function.prototype.method = function (name, func) {
    this.prototype[name] = func;
    return this;
};

Function.method('inherits', function (parent) {
    var d = 0, p = (this.prototype = new parent());
    this.method('uber', function uber(name) {
        var f, r, t = d, v = parent.prototype;
        if (t) {
            while (t) {
                v = v.constructor.prototype;
                t -= 1;
            }
            f = v[name];
        } else {
            f = p[name];
            if (f == this[name]) {
                f = v[name];
            }
        }
        d += 1;
        r = f.apply(this, Array.prototype.slice.apply(arguments, [1]));
        d -= 1;
        return r;
    });
    return this;
});

Function.method('swiss', function (parent) {
    for (var i = 1; i < arguments.length; i += 1) {
        var name = arguments[i];
        this.prototype[name] = parent.prototype[name];
    }
    return this;
});

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
