from pypy.rpython import objectmodel

def ll_stack_too_big():
    return objectmodel.stack_too_big()
ll_stack_too_big.suggested_primitive = True

def ll_stack_unwind():
    objectmodel.stack_unwind()
ll_stack_unwind.suggested_primitive = True

def ll_stack_check():
    if ll_stack_too_big():
        ll_stack_unwind()

