from pypy.rpython import rstack

def ll_stack_too_big():
    return rstack.stack_too_big()
ll_stack_too_big.suggested_primitive = True

def ll_stack_unwind():
    rstack.stack_unwind()
ll_stack_unwind.suggested_primitive = True

def ll_stack_check():
    if ll_stack_too_big():
        ll_stack_unwind()

