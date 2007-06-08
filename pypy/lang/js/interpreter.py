
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

def load_source(script_source):
    temp_tree = parse(script_source)
    return ASTBUILDER.dispatch(temp_tree)

def load_file(filename):
    f = open_file_as_stream(filename)
    t = load_source(f.readall())
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
        node = load_source(code.ToString(ctx))
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

class W_DateFake(W_NewBuiltin): # XXX This is temporary
    def Call(self, ctx, args=[], this=None):
        return create_object(ctx, 'Object')
    
    def Construct(self, ctx, args=[]):
        return create_object(ctx, 'Object')

class Interpreter(object):
    """Creates a js interpreter"""
    def __init__(self):
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
        
        w_ObjPrototype.Put('constructor', w_Object)
        w_ObjPrototype.Put('__proto__', w_Null)
        toString = W_ToString(ctx)
        w_ObjPrototype.Put('toString', toString)
        w_ObjPrototype.Put('toLocaleString', toString)
        w_ObjPrototype.Put('valueOf', W_ValueOf(ctx))
        w_ObjPrototype.Put('hasOwnProperty', W_HasOwnProperty(ctx))
        w_ObjPrototype.Put('isPrototypeOf', W_IsPrototypeOf(ctx))
        w_ObjPrototype.Put('propertyIsEnumerable', W_PropertyIsEnumerable(ctx))
        
        #properties of the function prototype
        w_FncPrototype.Put('constructor', w_FncPrototype)
        w_FncPrototype.Put('__proto__', w_ObjPrototype)
        w_FncPrototype.Put('toString', W_FToString(ctx))
        w_FncPrototype.Put('apply', W_Apply(ctx))
        w_FncPrototype.Put('call', W_Call(ctx))
        
        w_Boolean = W_BooleanObject('Boolean', w_FncPrototype)
        w_Boolean.Put('constructor', w_FncPrototype)
        
        w_BoolPrototype = create_object(ctx, 'Object', Value=W_Boolean(False))
        w_BoolPrototype.Class = 'Boolean'
        w_BoolPrototype.Put('constructor', w_FncPrototype)
        w_BoolPrototype.Put('toString', W_ValueToString(ctx))
        w_BoolPrototype.Put('valueOf', W_ValueValueOf(ctx))

        w_Boolean.Put('prototype', w_BoolPrototype)

        w_Global.Put('Boolean', w_Boolean)

        #Number
        w_Number = W_NumberObject('Number', w_FncPrototype)
        w_Number.Put('constructor', w_FncPrototype)

        w_NumPrototype = create_object(ctx, 'Object', Value=W_Number(0.0))
        w_NumPrototype.Class = 'Number'
        w_NumPrototype.Put('constructor', w_FncPrototype)
        w_NumPrototype.Put('toString', W_ValueToString(ctx))
        w_NumPrototype.Put('valueOf', W_ValueValueOf(ctx))

        w_Number.Put('prototype', w_NumPrototype)
        w_Number.Put('NaN', W_Number(NaN))
        w_Number.Put('POSITIVE_INFINITY', W_Number(Infinity))
        w_Number.Put('NEGATIVE_INFINITY', W_Number(-Infinity))

        w_Global.Put('Number', w_Number)
        
        
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
        
        w_Global.Put('String', W_Builtin(stringjs, Class='String'))

        w_Array = W_Builtin(arrayjs, Class='Array')
        w_Array.Put('__proto__',  w_ObjPrototype)
        w_Array.Put('prototype', w_ObjPrototype, dd=True, de=True, ro=True)
        
        #Global Properties
        w_Global.Put('Array', w_Array)
        w_Global.Put('version', W_Builtin(versionjs))
        
        #Date
        w_Date = W_DateFake(ctx, Class='Date')
        w_Global.Put('Date', w_Date)
        
        #Number
        w_Number = W_NumberObject('Number', w_FncPrototype)
        
        w_NumPrototype = create_object(ctx, 'Object', Value=W_Number(0.0))
        w_NumPrototype.Class = 'Number'
        w_NumPrototype.Put('constructor', w_FncPrototype)
        w_NumPrototype.Put('toString', W_ValueToString(ctx))
        w_NumPrototype.Put('valueOf', W_ValueValueOf(ctx))
        
        w_Number.Put('prototype', w_NumPrototype)
        w_Number.Put('NaN', W_Number(NaN))
        w_Number.Put('POSITIVE_INFINITY', W_Number(Infinity))
        w_Number.Put('NEGATIVE_INFINITY', W_Number(-Infinity))
        
        w_Global.Put('Number', w_Number)
        
        #String
        w_String = W_StringObject('String', w_FncPrototype)
        w_StrPrototype = create_object(ctx, 'Object', Value=W_String(''))
        w_StrPrototype.Class = 'String'
        w_StrPrototype.Put('constructor', w_FncPrototype)
        w_StrPrototype.Put('toString', W_ValueToString(ctx))
        w_StrPrototype.Put('valueOf', W_ValueValueOf(ctx))
        w_StrPrototype.Put('charAt', W_CharAt(ctx))
        w_StrPrototype.Put('concat', W_Concat(ctx))
        
        w_String.Put('prototype', w_StrPrototype)
        
        w_Global.Put('String', w_String)
        

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