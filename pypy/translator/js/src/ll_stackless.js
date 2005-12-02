// Stackless helper data and code

var slp_frame_stack_top    = null;
var slp_frame_stack_bottom = null;
var slp_return_value       = undefined;
var slp_stack_depth        = 0;

// This gets called with --log

function log(s) {
    try {
        alert(s);   // in browser
    } catch (e) {
        print('log: ' + s);   // commandline
    }
}

function function_name(func) {
    var s = func.toString().split("\n");
    s = s[0].length == 0 ? s[1] : s[0];
    s = s.split(' ')[1];
    s = s.split('(')[0];
    return s
}

// example function for testing

function ll_stackless_stack_frames_depth() {
    if (!slp_frame_stack_top) {
        LOG("ll_stackless_stack_frames_depth init");
	slp_frame_stack_top = slp_frame_stack_bottom = slp_new_frame_simple(ll_stackless_stack_frames_depth);
        return;
    }

    LOG("ll_stackless_stack_frames_depth resume");
    var f = slp_frame_stack_top;
    slp_frame_stack_top = null;
    for (var result = 0;f;result++) {
        f = f.f_back;
    }
    return result;
}

//

function ll_stack_too_big() {
    var result = slp_stack_depth > 500;   // Firefox has a recursion limit of 1000 (others allow more)
    LOG("ll_stack_to_big result=" + result);
    return result;
}

function slp_new_frame(targetvar, func, resume_blocknum, vars) {
    //LOG("slp_new_frame("+targetvar+","+function_name(func)+","+resume_blocknum+","+vars.toSource()+")");
    LOG("slp_new_frame("+function_name(func)+")");
    var f             = new Object();
    f.func            = func;
    f.targetvar       = targetvar;
    f.resume_blocknum = resume_blocknum;
    f.vars            = vars;
    f.f_back          = null;
    slp_frame_stack_bottom.f_back = f; // push below bottom, to keep stack
    slp_frame_stack_bottom        = f; // correctly sorted after unwind
}

function slp_new_frame_simple(func) {
    LOG("slp_new_frame_simple("+function_name(func)+")");
    var f             = new Object();
    f.func            = func;
    f.targetvar       = undefined;
    f.resume_blocknum = undefined;
    f.vars            = undefined;
    f.f_back          = null;
    return f;   // note: the non-simple version returns nothing
}

function ll_stack_unwind() {
    LOG("ll_stack_unwind");
    if (slp_frame_stack_top) {
        slp_frame_stack_top = null;
    } else {
        slp_frame_stack_top = slp_frame_stack_bottom = slp_new_frame_simple(ll_stack_unwind);
    }
    LOG('slp_frame_stack_top='+slp_frame_stack_top + ', slp_frame_stack_bottom='+slp_frame_stack_bottom)
    return slp_return_value;
}

function    slp_return_current_frame_to_caller() {
    LOG("slp_return_current_frame_to_caller");
    if (!slp_frame_stack_top)    log('!slp_frame_stack_top');
    if (!slp_frame_stack_bottom) log('!slp_frame_stack_bottom');
    var   result = slp_frame_stack_top;
    slp_frame_stack_bottom.f_back = slp_new_frame_simple(slp_end_of_yielding_function); //special case!
    slp_frame_stack_top = slp_frame_stack_bottom = null;  // stop unwinding
    return result;
}

function slp_end_of_yielding_function() {
    LOG("slp_end_of_yielding_function");
    if (!slp_frame_stack_top) log('slp_end_of_yielding_function !slp_frame_stack_top'); // can only resume from slp_return_current_frame_to_caller()
    if (!slp_return_value)    log('slp_end_of_yielding_function !slp_return_value');
    LOG('slp_return_value is going to ' + function_name(slp_return_value.func))
    slp_frame_stack_top = slp_return_value;
    return null;
}

function ll_stackless_switch(c) {
    LOG("ll_stackless_switch");
    var f;
    var result;
    if (slp_frame_stack_top) {  //resume
        LOG("slp_frame_stack_top != null, SWITCH");
        // ready to do the switch.  The current (old) frame_stack_top is f.f_back,
        // which we store where it will be found immediately after the switch
        f = slp_frame_stack_top;
        result = f.f_back;

        // grab the saved value of 'c' and do the switch
        slp_frame_stack_top = f.p0;
        return result;
    }

    LOG("slp_frame_stack_top == null");
    // first, unwind the current stack
    f = slp_new_frame_simple(ll_stackless_switch);
    f.p0 = c;
    slp_frame_stack_top = slp_frame_stack_bottom = f;
}

// main dispatcher loop

function slp_main_loop() {
    var f_back;
    while (true) {
        slp_frame_stack_bottom = null;
        pending = slp_frame_stack_top;

        while (true) {
            f_back           = pending.f_back;
            LOG('calling: ' + function_name(pending.func));
            slp_stack_depth  = 0;               // we are restarting to recurse
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
            if (slp_frame_stack_bottom.f_back) log('slp_frame_stack_bottom.f_back');
            slp_frame_stack_bottom.f_back = f_back;
        }
    }
}

function slp_entry_point(funcstring) {
    slp_stack_depth = 0;    /// initial stack depth
    var result = eval(funcstring);
    if (slp_frame_stack_bottom) { // get with dispatch loop when stack unwound
        slp_main_loop();
        result = slp_return_value;
    }
    return result;
}

// End of Stackless helper data and code
