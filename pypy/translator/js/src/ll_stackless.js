// Stackless helper data and code

slp_frame_stack_top    = null;
slp_frame_stack_bottom = null;
slp_resume_block       = 0;

// slp_restart_substate   = undefined; // XXX do we really need this?
slp_return_value       = undefined;
slp_targetvar          = undefined;
slp_function           = undefined;

function ll_stack_too_big() {
    return false; // XXX TODO use call depth here!
}

function slp_new_frame(state, resume_data) {
  f        = new Object();
  f.f_back = null;
  f.state  = state;
  f.resume_data = resume_data;
  return f;
}

function ll_stackless_stack_unwind() {
    if (slp_frame_stack_top) {
        slp_frame_stack_top = null; //odd
    } else {
        slp_frame_stack_top = slp_frame_stack_bottom = slp_new_frame(0);
    }
}
ll_stack_unwind = ll_stackless_stack_unwind;    // alias (XXX really need both?)

function    slp_return_current_frame_to_caller() {
  var   result = slp_frame_stack_top;
  slp_frame_stack_bottom.f_back = slp_new_frame(3);
  slp_frame_stack_top = slp_frame_stack_bottom = null;  // stop unwinding
  return result;
}

function slp_end_of_yielding_function() {
  slp_frame_stack_top = slp_return_value;
  return null;
}

function ll_stackless_switch(c) {
	var f;
	var result;
	if (slp_frame_stack_top) {  //resume
	    // ready to do the switch.  The current (old) frame_stack_top is
	    // f.f_back, which we store where it will be found immediately
	    // after the switch
	    f = slp_frame_stack_top;
	    result = f.f_back;

	    // grab the saved value of 'c' and do the switch
	    slp_frame_stack_top = f.p0;
	    return result;
        }

	// first, unwind the current stack
	f = slp_new_frame(2);
	f.p0 = c;
	slp_frame_stack_top = slp_frame_stack_bottom = f;
	return null;
}
ll_stackless_switch__frame_stack_topPtr = ll_stackless_switch;  // alias (XXX really need both?)

// example function for testing

function ll_stackless_stack_frames_depth() {
    if (slp_frame_stack_top) {
        f = slp_frame_stack_top;
        slp_frame_stack_top = null;
        for (var result = 0;f;result++) {
           f = f.f_back;
        }
        return result;
    } else {
	slp_frame_stack_top = slp_frame_stack_bottom = slp_new_frame(1);
	return -1;
    }
}

function slp_main_loop() {
    while (true) {
        slp_frame_stack_bottom = null;
        pending = slp_frame_stack_top;

        while (true) {
            f_back      = pending.f_back;

            // state     = pending.state;
            // fn        = slp_state_decoding_table[state].function;
            // signature = slp_state_decoding_table[state].signature;
            // if (fn) {
            //     slp_restart_substate = 0;
            // } else {
            //     slp_restart_substate = signature;
            //     state    -= signature;
            //     fn        = slp_state_decoding_table[state].function;
            //     signature = slp_state_decoding_table[state].signature;
            // }

            // Call back into the function...
            // Ignoring parameters because they get initialized in the function anyway!
            slp_return_value = pending.slp_function();

            if (slp_frame_stack_top)
                break;
            if (!f_back)
                return;
            pending = f_back;
            slp_frame_stack_top = pending;
        }
        
        // slp_frame_stack_bottom is usually non-null here, apart from
        // when returning from switch()
        if (slp_frame_stack_bottom)
            slp_frame_stack_bottom.f_back = f_back;
    }
}

function slp_standalone_entry_point() {
    var result = fn();  //XXX hardcoded for now
    if (slp_frame_stack_bottom) {
        // if the stack unwound we need to run the dispatch loop
        // to retrieve the actual result
        slp_main_loop();
        result = slp_return_value;
    }
    return result;
}

// End of Stackless helper data and code
