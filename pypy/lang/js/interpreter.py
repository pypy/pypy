
import math
from pypy.lang.js.jsparser import parse, ParseError
from pypy.lang.js.astbuilder import ASTBuilder
from pypy.lang.js.operations import *
from pypy.lang.js.jsobj import ThrowException
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.streamio import open_file_as_stream

ASTBUILDER = ASTBuilder()

def writer(x):
    print x

def load_source(script_source, sourcename):
    temp_tree = parse(script_source)
    ASTBUILDER.sourcename = sourcename
    return ASTBUILDER.dispatch(temp_tree)

def load_file(filename):
    f = open_file_as_stream(filename)
    t = load_source(f.readall(), filename)
    f.close()
    return t

class W_NativeObject(W_Object):
    def __init__(self, Class, Prototype, ctx=None,
                 Value=w_Undefined, callfunc=None):
        W_Object.__init__(self, ctx, Prototype,
                          Class, Value, callfunc)
    
class W_ObjectObject(W_NativeObject):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            return args[0].ToObject(ctx)
        else:
            return self.Construct(ctx)

    def Construct(self, ctx, args=[]):
        if len(args) >= 1 and not (isinstance(args[0], W_Undefined) \
                                    or isinstance(args[0], W_Null)):          
            # XXX later we could separate builtins and normal objects
            return args[0].ToObject(ctx)
        return create_object(ctx, 'Object')

class W_BooleanObject(W_NativeObject):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            return W_Boolean(args[0].ToBoolean())
        else:
            return W_Boolean(False)

    def Construct(self, ctx, args=[]):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            Value = W_Boolean(args[0].ToBoolean())
            return create_object(ctx, 'Boolean', Value = Value)
        return create_object(ctx, 'Boolean', Value = W_Boolean(False))

class W_NumberObject(W_NativeObject):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            return W_Number(args[0].ToNumber())
        else:
            return W_Number(0.0)

    def Construct(self, ctx, args=[]):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            Value = W_Number(args[0].ToNumber())
            return create_object(ctx, 'Number', Value = Value)
        return create_object(ctx, 'Number', Value = W_Number(0.0))

class W_StringObject(W_NativeObject):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            return W_String(args[0].ToString(ctx))
        else:
            return W_String('')

    def Construct(self, ctx, args=[]):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            Value = W_String(args[0].ToString(ctx))
            return create_object(ctx, 'String', Value = Value)
        return create_object(ctx, 'String', Value = W_String(''))

class W_ArrayObject(W_NativeObject):
    def Call(self, ctx, args=[], this=None):
        proto = ctx.get_global().Get('Array').Get('prototype')
        array = W_Array(ctx, Prototype=proto, Class = proto.Class)
        for i in range(len(args)):
            print "yeahh"
            array.Put(str(i), args[0])
        return array

    def Construct(self, ctx, args=[]):
        return self.Call(ctx, args)

TEST = False

def evaljs(ctx, args, this):
    if len(args) >= 1:
        if  isinstance(args[0], W_String):
            code = args[0]
        else:
            return args[0]
    else:
        code = W_String('')
    try:
        node = load_source(code.ToString(ctx), 'evalcode')
    except ParseError, e:
        raise ThrowException(W_String('SintaxError: '+str(e)))    
    
    if TEST:
        try:
            return node.execute(ctx)
        except ThrowException, e:
            return W_String("error")
    else:
        return node.execute(ctx)

def parseIntjs(ctx, args, this):
    if len(args) < 1:
        return W_Number(NaN)
    s = args[0].ToString(ctx).strip(" ")
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
    s = args[0].ToString(ctx).strip(" ")
    try:
        n = float(s)
    except ValueError:
        n = NaN
    return W_Number(n)
    

def printjs(ctx, args, this):
    writer(",".join([i.GetValue().ToString(ctx) for i in args]))
    return w_Undefined

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
        return W_String(args[0].ToString(ctx))
    return W_String('')

def arrayjs(ctx, args, this):
    arr = W_Array()
    for i in range(len(args)):
        arr.Put(str(i), args[i])
    return arr


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

def sqrtjs(ctx, args, this):
    return W_Number(math.sqrt(args[0].ToNumber()))

def versionjs(ctx, args, this):
    return w_Undefined

class W_ToString(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        return W_String("[object %s]"%this.Class)

class W_ValueOf(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        return this

class W_HasOwnProperty(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1:
            propname = args[0].ToString(ctx)
            if propname in this.propdict:
                return W_Boolean(True)
        return W_Boolean(False)

class W_IsPrototypeOf(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1 and isinstance(args[0], W_PrimitiveObject):
            O = this
            V = args[0].Prototype
            while V is not None:
                if O == V:
                    return W_Boolean(True)
                V = V.Prototype
        return W_Boolean(False)

class W_PropertyIsEnumerable(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1:
            propname = args[0].ToString(ctx)
            if propname in this.propdict and not this.propdict[propname].de:
                return W_Boolean(True)
        return W_Boolean(False)

class W_Function(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        tam = len(args)
        if tam >= 1:
            fbody  = args[tam-1].GetValue().ToString(ctx)
            argslist = []
            for i in range(tam-1):
                argslist.append(args[i].GetValue().ToString(ctx))
            fargs = ','.join(argslist)
            functioncode = "function (%s) {%s}"%(fargs, fbody)
        else:
            functioncode = "function () {}"
        #remove program and sourcelements node
        funcnode = parse(functioncode).children[0].children[0]
        return ASTBUILDER.dispatch(funcnode).execute(ctx)
    
    def Construct(self, ctx, args=[]):
        return self.Call(ctx, args, this=None)

functionstring= 'function (arguments go here!) {\n'+ \
                '    [lots of stuff :)]\n'+ \
                '}'
class W_FToString(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if this.Class == 'Function':
            return W_String(functionstring)
        else:
            raise JsTypeError('this is not a function object')

class W_Apply(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        try:
            if isnull_or_undefined(args[0]):
                thisArg = ctx.get_global()
            else:
                thisArg = args[0].ToObject(ctx)
        except IndexError:
            thisArg = ctx.get_global()
        
        try:
            arrayArgs = args[1]
            if isinstance(arrayArgs, W_ListObject):
                callargs = arrayArgs.tolist()
            elif isinstance(arrayArgs, W_Undefined) \
                    or isinstance(arrayArgs, W_Null):
                callargs = []
            else:
                raise JsTypeError('arrayArgs is not an Array or Arguments object')
        except IndexError:
            callargs = []
        return this.Call(ctx, callargs, this=thisArg)

class W_Call(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1:
            if isnull_or_undefined(args[0]):
                thisArg = ctx.get_global()
            else:
                thisArg = args[0]
            callargs = args[1:]
        else:
            thisArg = ctx.get_global()
            callargs = []
        return this.Call(ctx, callargs, this = thisArg)

class W_ValueToString(W_NewBuiltin):
    "this is the toString function for objects with Value"
    def Call(self, ctx, args=[], this=None):
        return W_String(this.Value.ToString(ctx))
    
class W_ValueValueOf(W_NewBuiltin):
    "this is the valueOf function for objects with Value"
    def Call(self, ctx, args=[], this=None):
        return this.Value

class W_CharAt(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        if len(args)>=1:
            pos = args[0].ToInt32()
            if (not pos >=0) or (pos > len(string) - 1):
                return W_String('')
        else:
            return W_String('')
        return W_String(string[pos])

class W_Concat(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        others = [obj.ToString(ctx) for obj in args]
        string += ''.join(others)
        return W_String(string)

class W_IndexOf(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        if len(args) < 1:
            return W_Number(-1.0)
        substr = args[0].ToString(ctx)
        size = len(string)
        subsize = len(substr)
        if len(args) < 2:
            pos = 0
        else:
            pos = args[1].ToInt32()
        pos = min(max(pos, 0), size)
        return W_Number(string.find(substr, pos))

class W_Substring(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        size = len(string)
        if len(args) < 1:
            start = 0
        else:
            start = args[0].ToInt32()
        if len(args) < 2:
            end = size
        else:
            end = args[1].ToInt32()
        tmp1 = min(max(start, 0), size)
        tmp2 = min(max(end, 0), size)
        start = min(tmp1, tmp2)
        end = max(tmp1, tmp2)
        return W_String(string[start:end])

class W_ArrayToString(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        length = this.Get('length').ToUInt32()
        sep = ','
        return W_String(sep.join([this.Get(str(index)).ToString(ctx) 
                            for index in range(length)]))

class W_DateFake(W_NewBuiltin): # XXX This is temporary
    def Call(self, ctx, args=[], this=None):
        return create_object(ctx, 'Object')
    
    def Construct(self, ctx, args=[]):
        return create_object(ctx, 'Object')

class Interpreter(object):
    """Creates a js interpreter"""
    def __init__(self):
        def put_values(obj, dictvalues):
            for key,value in dictvalues.iteritems():
                obj.Put(key, value)
            
        w_Global = W_Object(Class="global")

        ctx = global_context(w_Global)
        
        w_ObjPrototype = W_Object(Prototype=None, Class='Object')
        
        w_Function = W_Function(ctx, Class='Function', 
                              Prototype=w_ObjPrototype)
        
        w_Global.Put('Function', w_Function)
        
        w_Object = W_ObjectObject('Object', w_Function)
        w_Object.Put('prototype', w_ObjPrototype, dd=True, de=True, ro=True)
        
        w_Global.Put('Object', w_Object)
        w_FncPrototype = w_Function.Call(ctx, this=w_Function)
        w_Function.Put('prototype', w_FncPrototype, dd=True, de=True, ro=True)
        w_Function.Put('constructor', w_Function)
        
        w_Object.Put('length', W_Number(1), ro=True, dd=True)
        
        toString = W_ToString(ctx)
        
        put_values(w_ObjPrototype, {
            'constructor': w_Object,
            '__proto__': w_Null,
            'toString': toString,
            'toLocaleString': toString,
            'valueOf': W_ValueOf(ctx),
            'hasOwnProperty': W_HasOwnProperty(ctx),
            'isPrototypeOf': W_IsPrototypeOf(ctx),
            'propertyIsEnumerable': W_PropertyIsEnumerable(ctx),
        })
        
        #properties of the function prototype
        put_values(w_FncPrototype, {
            'constructor': w_FncPrototype,
            '__proto__': w_ObjPrototype,
            'toString': W_FToString(ctx),
            'apply': W_Apply(ctx),
            'call': W_Call(ctx),        
        })
        
        w_Boolean = W_BooleanObject('Boolean', w_FncPrototype)
        w_Boolean.Put('constructor', w_FncPrototype)
        
        w_BoolPrototype = create_object(ctx, 'Object', Value=W_Boolean(False))
        w_BoolPrototype.Class = 'Boolean'
        
        put_values(w_BoolPrototype, {
            'constructor': w_FncPrototype,
            '__proto__': w_BoolPrototype,
            'toString': W_ValueToString(ctx),
            'valueOf': W_ValueValueOf(ctx),
        })

        w_Boolean.Put('prototype', w_BoolPrototype)

        w_Global.Put('Boolean', w_Boolean)

        #Number
        w_Number = W_NumberObject('Number', w_FncPrototype)

        w_NumPrototype = create_object(ctx, 'Object', Value=W_Number(0.0))
        w_NumPrototype.Class = 'Number'
        put_values(w_NumPrototype, {
            'constructor': w_FncPrototype,
            '__proto__': w_NumPrototype,
            'toString': W_ValueToString(ctx),
            'valueOf': W_ValueValueOf(ctx),
        })

        put_values(w_Number, {
            'constructor': w_FncPrototype,
            'prototype': w_NumPrototype,
            'NaN': W_Number(NaN),
            'POSITIVE_INFINITY': W_Number(Infinity),
            'NEGATIVE_INFINITY': W_Number(-Infinity),
        })

        w_Global.Put('Number', w_Number)
        
                
        #String
        w_String = W_StringObject('String', w_FncPrototype)

        w_StrPrototype = create_object(ctx, 'Object', Value=W_String(''))
        w_StrPrototype.Class = 'String'
        
        put_values(w_StrPrototype, {
            'constructor': w_FncPrototype,
            '__proto__': w_StrPrototype,
            'toString': W_ValueToString(ctx),
            'valueOf': W_ValueValueOf(ctx),
            'charAt': W_CharAt(ctx),
            'concat': W_Concat(ctx),
            'indexOf': W_IndexOf(ctx),
            'substring': W_Substring(ctx),
        })
        
        w_String.Put('prototype', w_StrPrototype)
        w_Global.Put('String', w_String)

        w_Array = W_ArrayObject('Array', w_FncPrototype)

        w_ArrPrototype = create_object(ctx, 'Object')
        w_ArrPrototype.Class = 'Array'
        
        put_values(w_ArrPrototype, {
            'constructor': w_FncPrototype,
            '__proto__': w_ArrPrototype,
            'toString': W_ArrayToString(ctx),
        })
        
        w_Array.Put('prototype', w_ArrPrototype)
        w_Global.Put('Array', w_Array)
        
        
        #Math
        w_math = W_Object(Class='Math')
        w_Global.Put('Math', w_math)
        w_math.Put('__proto__',  w_ObjPrototype)
        w_math.Put('prototype', w_ObjPrototype, dd=True, de=True, ro=True)
        w_math.Put('abs', W_Builtin(absjs, Class='function'))
        w_math.Put('floor', W_Builtin(floorjs, Class='function'))
        w_math.Put('pow', W_Builtin(powjs, Class='function'))
        w_math.Put('sqrt', W_Builtin(sqrtjs, Class='function'))
        w_math.Put('E', W_Number(math.e))
        w_math.Put('PI', W_Number(math.pi))
        
        w_Global.Put('version', W_Builtin(versionjs))
        
        #Date
        w_Date = W_DateFake(ctx, Class='Date')
        w_Global.Put('Date', w_Date)
        
        w_Global.Put('NaN', W_Number(NaN))
        w_Global.Put('Infinity', W_Number(Infinity))
        w_Global.Put('undefined', w_Undefined)
        w_Global.Put('eval', W_Builtin(evaljs))
        w_Global.Put('parseInt', W_Builtin(parseIntjs))
        w_Global.Put('parseFloat', W_Builtin(parseFloatjs))
        w_Global.Put('isNaN', W_Builtin(isnanjs))
        w_Global.Put('isFinite', W_Builtin(isnanjs))            

        w_Global.Put('print', W_Builtin(printjs))
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
        elif isinstance(arg, int) or isinstance(arg, float) \
                                    or isinstance(arg, long):
            res.append(W_Number(arg))
        elif isinstance(arg, bool):
            res.append(W_Boolean(arg))
    return res