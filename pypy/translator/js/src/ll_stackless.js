// Stackless helper data and code

var slp_frame_stack_top    = null;
var slp_frame_stack_bottom = null;
var slp_return_value       = undefined;
var slp_debug              = false;

function logme(s) {
    if (slp_debug) {
        print("logme: " + s);
    }
}

function ll_stack_too_big_helper(depth) {
    if (depth > 0) {   
        ll_stack_too_big_helper(depth-1)
    }
}   

function ll_stack_too_big() {
    try {
        ll_stack_too_big_helper(5); //XXX
    } catch (e) {   //stack overflow when recursing some more
        return true;  
    }
    return false;
} 

function slp_new_frame(targetvar, func, resume_blocknum, vars) {
    if (slp_debug)  logme("starting slp_new_frame("+targetvar+","+func.toString().split("\n")[1]+","+resume_blocknum+","+vars.toSource()+")");
    var f             = new Object();
    f.func            = func;
    f.targetvar       = targetvar;
    f.resume_blocknum = resume_blocknum;
    f.vars            = vars;
    f.f_back          = null;
    // push below current bottom so after unwinding the current stack
    // the slp_frame_stack will be correctly sorted
    slp_frame_stack_bottom.f_back = f;
    slp_frame_stack_bottom        = f;
    if (slp_debug)  logme("finished slp_new_frame");
}

function slp_new_frame_simple(func) {
    if (slp_debug)  logme("starting slp_new_frame_simple("+func.toString().split("\n")[1]+")");
    var f             = new Object();
    f.func            = func;
    f.targetvar       = undefined;
    f.resume_blocknum = undefined;
    f.vars            = undefined;
    f.f_back          = null;
    if (slp_debug)  logme("finished slp_new_frame_simple");
    return f;   // note: the non-simple version returns nothing
}

// <UNTESTED>

function ll_stackless_stack_unwind() {
    if (slp_debug)  logme("starting ll_stackless_stack_unwind");
    if (slp_frame_stack_top) {
        slp_frame_stack_top = null; // no need to resume
    } else {
        slp_frame_stack_top = slp_frame_stack_bottom = slp_new_frame_simple(ll_stackless_stack_unwind);
    }
    if (slp_debug)  logme("finished ll_stackless_stack_unwind");
}
ll_stack_unwind = ll_stackless_stack_unwind;    // alias (XXX really need both?)

function    slp_return_current_frame_to_caller() {
    if (slp_debug)  logme("starting slp_return_current_frame_to_caller");
    if (!slp_frame_stack_top) alert('!slp_frame_stack_top');
    if (!slp_frame_stack_bottom) alert('!slp_frame_stack_bottom');
    var   result = slp_frame_stack_top;
    slp_frame_stack_bottom.f_back = slp_new_frame_simple(slp_return_current_frame_to_caller);
    slp_frame_stack_top = slp_frame_stack_bottom = null;  // stop unwinding
    if (slp_debug)  logme("finished slp_return_current_frame_to_caller");
    return result;
}

function slp_end_of_yielding_function() {
    if (slp_debug)  logme("starting slp_end_of_yielding_function");
    if (!slp_frame_stack_top) alert('!slp_frame_stack_top'); // can only resume from slp_return_current_frame_to_caller()
    if (!slp_return_value) alert('!slp_return_value');
    slp_frame_stack_top = slp_return_value;
    if (slp_debug)  logme("finished slp_end_of_yielding_function");
    return null;  // XXX or just return?
}

function ll_stackless_switch(c) {
    if (slp_debug)  logme("starting ll_stackless_switch");
    var f;
    var result;
    if (slp_frame_stack_top) {  //resume
        if (slp_debug)  logme("slp_frame_stack_top != null");
        // ready to do the switch.  The current (old) frame_stack_top is
        // f.f_back, which we store where it will be found immediately
        // after the switch
        f = slp_frame_stack_top;
        result = f.f_back;

        // grab the saved value of 'c' and do the switch
        slp_frame_stack_top = f.p0;
        if (slp_debug)  logme("finished ll_stackless_switch");
        return result;
    }

    if (slp_debug)  logme("slp_frame_stack_top == null");
    // first, unwind the current stack
    f = slp_new_frame_simple(ll_stackless_switch);
    f.p0 = c;
    slp_frame_stack_top = slp_frame_stack_bottom = f;
    if (slp_debug)  logme("finished ll_stackless_switch");
    return null;
}
ll_stackless_switch__frame_stack_topPtr = ll_stackless_switch;  // alias (XXX really need both?)

// </UNTESTED>

// example function for testing

function ll_stackless_stack_frames_depth() {
    if (!slp_frame_stack_top) {
        if (slp_debug) logme("starting ll_stackless_stack_frames_depth init");
	slp_frame_stack_top = slp_frame_stack_bottom = slp_new_frame_simple(ll_stackless_stack_frames_depth);
        if (slp_debug) logme("finished ll_stackless_stack_frames_depth init");
        return;
    }

    if (slp_debug) logme("starting ll_stackless_stack_frames_depth resume");
    var f = slp_frame_stack_top;
    slp_frame_stack_top = null;
    for (var result = 0;f;result++) {
        f = f.f_back;
    }
    if (slp_debug) logme("stack_frames_depth = " + result);
    if (slp_debug) logme("finished ll_stackless_stack_frames_depth resume");
    return result;
}

function slp_main_loop() {
    var f_back;
    if (slp_debug) logme("starting slp_main_loop");
    while (true) {
        if (slp_debug) logme("slp_main_loop (outer loop)");
    
        slp_frame_stack_bottom = null;
        pending = slp_frame_stack_top;

        while (true) {
            if (slp_debug) logme("slp_main_loop (inner loop)");
            f_back           = pending.f_back;
            logme('calling: ' + pending.func.toString().split('\n')[1]);
            slp_return_value = pending.func();  // params get initialized in the function because it's a resume!
            if (slp_frame_stack_top) {
                break;
            }
            if (!f_back) {
                return;
            }
            pending             = f_back;
            slp_frame_stack_top = pending;
        }
        
        if (slp_frame_stack_bottom) { // returning from switch()
            if (slp_frame_stack_bottom.f_back) alert('slp_frame_stack_bottom.f_back');
            slp_frame_stack_bottom.f_back = f_back;
        }
    }
    if (slp_debug) logme("finished slp_main_loop");
}

function slp_entry_point(funcstring) {
    if (slp_debug) logme("starting slp_standalone_entry_point");
    var result = eval(funcstring);
    if (slp_frame_stack_bottom) {
        // if the stack unwound we need to run the dispatch loop
        // to retrieve the actual result
        slp_main_loop();
        result = slp_return_value;
    }
    if (slp_debug) logme("finished slp_standalone_entry_point");
    return result;
}

// End of Stackless helper data and code
