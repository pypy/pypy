from pypy.rpython import objectmodel

def ll_stackless_stack_frames_depth():
    return objectmodel.stack_frames_depth()
ll_stackless_stack_frames_depth.suggested_primitive = True
