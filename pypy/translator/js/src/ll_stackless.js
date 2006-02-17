// Stackless helper data and code

var slp_frame_stack_top    = null;
var slp_frame_stack_bottom = null;
var slp_return_value       = undefined;

var slp_timeout            = false;
var slp_start_time         = undefined;
var slp_start_time0        = undefined;
var slp_stack_depth        = 0;
var slp_max_stack_depth    = 75;    // XXX make this browser dependent (75:Safari, 750:Firefox/Spidermonkey, more:IE)

function function_name(func) {
    var s = func.toString().split("\n");
    s = s[0].length == 0 ? s[1] : s[0];
    s = s.split(' ')[1];
    s = s.split('(')[0];
    return s
}

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
ll_stackless_stack_frames_depth___ = ll_stackless_stack_frames_depth;

//

function ll_stack_too_big() {
    var result = slp_stack_depth > slp_max_stack_depth;   // Firefox has a recursion limit of 1000 (others allow more)
    LOG("ll_stack_to_big result=" + result);

    if (!result && in_browser) {
        var t = new Date().getTime();
        var d = t - slp_start_time;
        result = d > 100;
        if (result) {
            slp_timeout = true;
        } 
    }
    return result;
}
ll_stack_too_big___ = ll_stack_too_big;

function slp_new_frame(targetvar, func, resume_blocknum, varnames, vars) {
    LOG("slp_new_frame("+function_name(func)+")");
    var f = {func:func, vars:vars, f_back:null};
    var s = "block=" + resume_blocknum + ";";
    for (var i = 0;i < vars.length;i++) {
        if (varnames[i] == targetvar) {
            s += targetvar + "=slp_return_value;";
        } else {
            s += varnames[i]  + "=slp_frame_stack_top.vars[" + i + "];";
        }
    }
    s += "slp_frame_stack_top=null;";
    f.resumecode = s;
    slp_frame_stack_bottom.f_back = f; // push below bottom, to keep stack
    slp_frame_stack_bottom        = f; // correctly sorted after unwind
    LOG(f.resumecode);
}

function slp_new_frame_simple(func) {
    LOG("slp_new_frame_simple("+function_name(func)+")");
    return {func:func, f_back:null};    // note: the non-simple version returns nothing
}

function ll_stack_unwind() {
    LOG("ll_stack_unwind");
    if (slp_frame_stack_top) {
        slp_frame_stack_top = null;
    } else {
        slp_frame_stack_top = slp_frame_stack_bottom = slp_new_frame_simple(ll_stack_unwind);
    }
    LOG('slp_frame_stack_top='+slp_frame_stack_top + ', slp_frame_stack_bottom='+slp_frame_stack_bottom);
    return slp_return_value;
}
ll_stack_unwind___ = ll_stack_unwind;

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
    LOG('slp_return_value is going to ' + function_name(slp_return_value.func));
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
ll_stackless_switch__frame_stack_topPtr = ll_stackless_switch;

// main dispatcher loop

slp_main_loop_counter = 0;

function slp_main_loop() {
    var f_back;
    LOG("SLP_MAIN_LOOP");
    slp_timeout    = false;
    slp_start_time = new Date().getTime();

    if (in_browser) {
        slp_main_loop_counter += 1;
        var f = slp_frame_stack_top;
        for (var n_frames= 0;f;n_frames++) {
            f = f.f_back;
        }  
        document.title = "time="+(slp_start_time - slp_start_time0) / 1000.0 + ", slp_main_loop_counter="+slp_main_loop_counter + ", slp_stack_depth="+slp_stack_depth + ", n_frames="+n_frames;
    }

    while (true) {
        slp_frame_stack_bottom = null;
        pending = slp_frame_stack_top;

        while (true) {
            f_back           = pending.f_back;
            LOG('calling: ' + function_name(pending.func));
            slp_stack_depth  = 0;               // we are restarting to recurse
            slp_return_value = pending.func();  // params get initialized in the function because it's a resume!
            //if (slp_timeout) {
            //    setTimeout('slp_main_loop()', 0);
            //    return undefined;
            //}
            if (slp_frame_stack_top) {
                break;
            }
            if (!f_back) {
                return;
            }
            pending             = f_back;
            slp_frame_stack_top = pending;
            if (slp_timeout) {
                setTimeout('slp_main_loop()', 0);
                return undefined;
            }
        }

        if (slp_frame_stack_bottom) { // returning from switch()
            if (slp_frame_stack_bottom.f_back) log('slp_frame_stack_bottom.f_back');
            slp_frame_stack_bottom.f_back = f_back;
        }
    }
    LOG("REALLY FINISHED");
    handle_result(slp_return_value);
}

// 
// note: this function returns undefined for long running processes.
//        In that case it should be seen as similar to thread.run()
//
function slp_entry_point(funcstring) {  //new thread().run()
    slp_timeout     = false;
    slp_start_time  = new Date().getTime();
    slp_start_time0 = slp_start_time;
    slp_stack_depth = 0;    /// initial stack depth
    var result = eval(funcstring);
    if (slp_frame_stack_bottom) { // get with dispatch loop when stack unwound
        if (slp_timeout) {
            setTimeout('slp_main_loop()', 0);
            return undefined;
        }
        slp_main_loop();
        result = slp_return_value;
    }
    if (typeof(result) == typeof({})) {
        result = result.chars;  //assume it's a rpystring
    }
    return result;
}

// End of Stackless helper data and code
