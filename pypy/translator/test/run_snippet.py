""" 

    Use all functions in snippet to test translation to pyrex
    
"""
import autopath
import traceback
import sys
from pypy.translator.translator import Translator

from pypy.translator.test import snippet

class Result:
    def __init__(self, func, argtypes):
        self.func = func 
        self.argtypes = argtypes
        self.r_flow = self.r_annotate = self.r_compile = None 
        for name in 'flow', 'annotate', 'compile':
            method = getattr(self, name)
            resname = 'r_' + name 
            try:
                method()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                self.excinfo = sys.exc_info()
                setattr(self, resname, False) 
            else:
                setattr(self, resname, True) 
                
    def flow(self):
        self.translator = Translator(func)
        self.translator.simplify()

    def annotate(self):
        self.translator.annotate(self.argtypes)

    def compile(self):
        compiled_function = self.translator.compile()
        return compiled_function
    
def collect_functions(module, specnamelist):
    l = []
    for funcname, value in vars(module).items():
        if not hasattr(value, 'func_code'):
            continue
        for specname in specnamelist:
            if funcname.startswith(specname):
                l.append(value)
                break
        if not specnamelist:
            l.append(value) 
    return l
  
 
def combine(lists):
    if not lists:
        yield []
    else:
        head = lists[0]
        if not isinstance(head, tuple):
            head = (head,)
        tail = lists[1:]
        for item in head:
            for com in combine(tail):
                yield [item] + com 

def get_arg_types(func):
    # func_defaults e.g.:  ([int, float], [str, int], int) 
    if func.func_defaults:
        for argtypeslist in combine(func.func_defaults):
            yield argtypeslist 
    else:
        yield []

# format string for result-lines 
format_str = "%-30s %10s %10s %10s" 

def repr_result(res):
    name = res.func.func_name 
    argtypes = res.argtypes 
    funccall = "%s(%s)" % (name, ", ".join([x.__name__ for x in argtypes]))
    flow = res.r_flow and 'ok' or 'fail' 
    ann = res.r_annotate and 'ok' or 'fail'
    comp = res.r_compile and 'ok' or 'fail'
    return format_str %(funccall, flow, ann, comp)
     
if __name__=='__main__':
    specnamelist = sys.argv[1:]
    funcs = collect_functions(snippet, specnamelist) 
    results = []
    print format_str %("functioncall", "flowed", "annotated", "compiled")
    for func in funcs:
        for argtypeslist in get_arg_types(func):
            #print "trying %s %s" %(func, argtypeslist)
            result = Result(func, argtypeslist) 
            results.append(result) 
            print repr_result(result) 
            if specnamelist and getattr(result, 'excinfo', None): 
                traceback.print_exception(*result.excinfo) 
                raise SystemExit, 1
    
    #for res in results:
    #    print repr_result(res) 
   
     
