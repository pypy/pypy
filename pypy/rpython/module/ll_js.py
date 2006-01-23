from pypy.rpython import rjs

def ll_js_jseval(s):
    return rjs.jseval(s)
ll_js_jseval.suggested_primitive = True
