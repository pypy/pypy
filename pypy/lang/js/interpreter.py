
import math
from pypy.lang.js.jsparser import parse
from pypy.lang.js.astbuilder import ASTBuilder
from pypy.lang.js.operations import *
from pypy.rlib.objectmodel import we_are_translated


def writer(x):
    print x

def load_source(script_source):
    astb = ASTBuilder()
    temp_tree = parse(script_source)
    return astb.dispatch(temp_tree)

import os.path

def load_file(filename):
    # NOT RPYTHON
    base, ext = os.path.splitext(filename)
    f = open(filename)
    t = load_source(f.read())
    f.close()
    return t
    

def evaljs(ctx, args, this):
    if len(args) >= 1:
        if  isinstance(args[0],W_String):
            code = args[0]
        else:
            return args[0]
    else:
        code = W_String('')
    return load_source(code.ToString()).execute(ctx)

def functionjs(ctx, args, this):
    tam = len(args)
    if tam >= 1:
        fbody  = args[tam-1].GetValue().ToString()
        argslist = []
        for i in range(tam-1):
            argslist.append(args[i].GetValue().ToString())
        fargs = ','.join(argslist)
        functioncode = "__anon__ = function (%s) {%s}"%(fargs, fbody)
    else:
        functioncode = "__anon__ = function () {}"
    return evaljs(ctx, [W_String(functioncode),], this)

def parseIntjs(ctx, args, this):
    if len(args) < 1:
        return W_Number(NaN)
    s = args[0].ToString().strip(" ")
    if len(args) > 1:
        radix = args[1].ToInt32()
    else:
        radix = 10
    if len(s) >= 2 and (s.startswith('0x') or s.startswith('0X')) :
        radix = 16
        s = s[2:]
    if s == '' or radix < 2 or radix > 36:
        return W_Number(NaN)
    try:
        n = int(s, radix)
    except ValueError:
        n = NaN
    return W_Number(n)

def parseFloatjs(ctx, args, this):
    if len(args) < 1:
        return W_Number(NaN)
    s = args[0].ToString().strip(" ")
    try:
        n = float(s)
    except ValueError:
        n = NaN
    return W_Number(n)
    

def printjs(ctx, args, this):
    writer(",".join([i.GetValue().ToString() for i in args]))
    return w_Undefined

def objectconstructor(ctx, args, this):
    return W_Object()

def isnanjs(ctx, args, this):
    if len(args) < 1:
        return W_Boolean(True)
    return W_Boolean(args[0].ToNumber() == NaN)

def isfinitejs(ctx, args, this):
    if len(args) < 1:
        return W_Boolean(True)
    n = args[0].ToNumber()
    if n == Infinity or n == -Infinity or n == NaN:
        return W_Boolean(False)
    else:
        return W_Boolean(True)

def booleanjs(ctx, args, this):
    if len(args) > 0:
        return W_Boolean(args[0].ToBoolean())
    return W_Boolean(False)

def stringjs(ctx, args, this):
    if len(args) > 0:
        return W_String(args[0].ToString())
    return W_String('')

def numberjs(ctx, args, this):
    if len(args) > 0:
        return W_Number(args[0].ToNumber())
    return W_Number(0)
        
def absjs(ctx, args, this):
    return W_Number(abs(args[0].ToNumber()))

def floorjs(ctx, args, this):
    return W_Number(math.floor(args[0].ToNumber()))

def powjs(ctx, args, this):
    return W_Number(math.pow(args[0].ToNumber(), args[1].ToNumber()))
    
def versionjs(ctx, args, this):
    return w_Undefined

class Interpreter(object):
    """Creates a js interpreter"""
    def __init__(self):
        w_Global = W_Object(Class="global")
        ctx = global_context(w_Global)

        w_ObjPrototype = W_Object(Prototype=None, Class='Object')
        
        #Function stuff
        w_Function = W_Builtin(functionjs, ctx=ctx, Class='Function', 
                              Prototype=w_ObjPrototype)
        w_Function.Put('prototype', w_Function, dd=True, de=True, ro=True)
        w_Function.Put('constructor', w_Function)
        
        #Object stuff
        w_Object = W_Builtin(objectconstructor, Prototype=w_Function)
        w_Object.Put('length', W_Number(1), ro=True, dd=True)
        w_Object.Put('prototype', w_ObjPrototype, dd=True, de=True, ro=True)
        w_ObjPrototype.Put('constructor', w_Object)
        #And some other stuff
        
        #Math
        w_math = W_Object(Class='Math')
        w_Global.Put('Math', w_math)
        w_math.Put('__proto__',  w_ObjPrototype)
        w_math.Put('abs', W_Builtin(absjs, Class='function'))
        w_math.Put('floor', W_Builtin(floorjs, Class='function'))
        w_math.Put('pow', W_Builtin(powjs, Class='function'))
        w_math.Put('E', W_Number(math.e))
        w_math.Put('PI', W_Number(math.pi))
        
        w_Global.Put('String', W_Builtin(stringjs, Class='String'))
        
        #Global Properties
        w_Global.Put('Object', w_Object)
        w_Global.Put('Function', w_Function)
        w_Global.Put('Array', W_Array())
        w_Global.Put('version', W_Builtin(versionjs))
        
        #Number
        w_Date = W_Object(Class="Number")
        w_Global.Put('Date', w_Date)
        
        #Number
        w_Number = W_Builtin(numberjs, Class="Number")
        w_Number.Put('NaN', W_Number(NaN))
        w_Number.Put('POSITIVE_INFINITY', W_Number(Infinity))
        w_Number.Put('NEGATIVE_INFINITY', W_Number(-Infinity))
        w_Global.Put('Number', w_Number)
        
        w_Global.Put('Boolean', W_Builtin(booleanjs, Class="Boolean"))

        w_Global.Put('eval', W_Builtin(evaljs))
        w_Global.Put('print', W_Builtin(printjs))
        w_Global.Put('isNaN', W_Builtin(isnanjs))
        w_Global.Put('isFinite', W_Builtin(isnanjs))            
        w_Global.Put('parseFloat', W_Builtin(parseFloatjs))
        w_Global.Put('parseInt', W_Builtin(parseIntjs))
        w_Global.Put('NaN', W_Number(NaN))
        w_Global.Put('Infinity', W_Number(Infinity))
        w_Global.Put('undefined', w_Undefined)
        w_Global.Put('this', w_Global)
        
        
        self.global_context = ctx
        self.w_Global = w_Global
        self.w_Object = w_Object

    def run(self, script):
        """run the interpreter"""
        return script.execute(self.global_context)

def wrap_arguments(pyargs):
    "receives a list of arguments and wrap then in their js equivalents"
    res = []
    for arg in pyargs:
        if isinstance(arg, W_Root):
            res.append(arg)
        elif isinstance(arg, str):
            res.append(W_String(arg))
        elif isinstance(arg, int) or isinstance(arg, float) or isinstance(arg, long):
            res.append(W_Number(arg))
        elif isinstance(arg, bool):
            res.append(W_Boolean(arg))
    return res