function logme(s) {
    print("logme: " + s);
}

function ll_stack_too_big_helper(depth) {
    if (depth > 0) {
        ll_stack_too_big_helper(depth-1)
    }
}

function ll_stack_too_big() {
    try {
        ll_stack_too_big_helper(10); //XXX
    } catch (e) {   //stack overflow when recursing some more
        return true;
    }
    return false;
}
