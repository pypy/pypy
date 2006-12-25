
from pypy.lang.js.astgen import *
from pypy.lang.js.jsparser import parse
from pypy.lang.js.jsobj import *

def writer(x):
    print x

class Interpreter(object):
    """Creates a js interpreter"""
    def __init__(self, script_source=None):
        self.w_Object = W_Object() #creating Object
        self.w_Global = W_Object()
        self.w_Global.Prototype = self.w_Object
        self.w_Global.Put('prototype', 'Object')
        self.w_Global.Put('Object', self.w_Object)
        self.global_context = global_context(self.w_Global)
        if script_source is not None:
            self.load_source(script_source)
    
    def load_source(self, script_source):
        """load a source script text to the interpreter"""
        temp_dict = parse(script_source)
        self.script = from_dict(temp_dict)
    
    def run(self):
        """run the interpreter"""
        return self.script.call(self.global_context)

        

class __extend__(Array):
    def call(self, ctx):
        d = dict(enumerate(self.items))
        return W_Array(d)

class __extend__(Assign):
    def call(self, ctx):
        print "Assign LHS = ", self.LHSExp
        v1 = self.LHSExp.call(ctx)
        print "Assign Exp = ", self.AssignmentExp
        v3 = self.AssignmentExp.call(ctx).GetValue()
        v1.PutValue(v3, ctx)
        return v3

class __extend__(Block):
    def call(self, ctx):
        try:
            last = w_Undefined
            for node in self.nodes:
                last = node.call(ctx)
            return last
        except ExecutionReturned, e:
            return e.value

class __extend__(Call):
    def call(self, ctx):
        name = self.identifier.get_literal()
        if name == 'print':
            writer(",".join([i.GetValue().ToString() for i in self.arglist.call(ctx)]))
        else:    
            w_obj = ctx.resolve_identifier(name).GetValue()
            print "arglist = ", self.arglist
            retval = w_obj.Call(ctx=ctx, args=[i for i in self.arglist.call(ctx)])
            return retval

class __extend__(Comma):
    def call(self, ctx):
        self.left.call(ctx)
        return self.right.call(ctx)

class __extend__(Dot):
    def call(self, ctx):
        w_obj = self.left.call(ctx).GetValue().ToObject()
        name = self.right.get_literal()
        return Reference(name, w_obj)

class __extend__(Function):
    def call(self, ctx):
       w_obj = W_FunctionObject(self, ctx)
       return w_obj

class __extend__(Identifier):
    def call(self, ctx):
        if self.initialiser is not None:
            ref = ctx.resolve_identifier(self.name)
            ref.PutValue(self.initialiser.call(ctx), ctx)
        return ctx.resolve_identifier(self.name)
    
    def get_literal(self):
        return self.name

class __extend__(If):
    def call(self, ctx=None):
        temp = self.condition.call(ctx)
        print "if condition = ", temp 
        if temp.ToBoolean():
            return self.thenPart.call(ctx)
        else:
            return self.elsePart.call(ctx)

class __extend__(Group):
    def call(self, ctx = None):
        return self.expr.call(ctx)

def ARC(x, y):
    """
    Implements the Abstract Relational Comparison x < y
    Still not 100% to the spec
    """
    # TODO complete the funcion with strings comparison
    s1 = x.ToPrimitive('Number')
    s2 = y.ToPrimitive('Number')
    print "ARC x = %s, y = %s"%(str(s1),str(s2))
    if not (isinstance(s1, W_String) and isinstance(s2, W_String)):
        s4 = s1.ToNumber()
        s5 = s2.ToNumber()
        if s4 == NaN or s5 == NaN:
            return None
        if s4 < s5:
            return True
        else:
            return False
    else:
        pass 

class __extend__(Gt):
    def call(self, ctx = None):
        s2 = self.left.call(ctx).GetValue()
        s4 = self.right.call(ctx).GetValue()
        s5 = ARC(s4, s2)
        if s5 is None:
            return W_Boolean(False)
        else:
            return W_Boolean(s5)

class __extend__(Lt):
    def call(self, ctx = None):
        s2 = self.left.call(ctx).GetValue()
        s4 = self.right.call(ctx).GetValue()
        s5 = ARC(s2, s4)
        print "< ARC result = ", s5
        if s5 is None:
            return W_Boolean(False)
        else:
            return W_Boolean(s5)

class __extend__(Index):
    def call(self, ctx=None):
        w_obj = self.left.call(ctx).GetValue()
        w_member = self.expr.call(ctx).GetValue()
        w_obj = w_obj.ToObject()
        name = w_member.ToString()
        return w_obj.Get(name)

class __extend__(List):
    def call(self, ctx):
        print "nodes = ", self.nodes
        return [node.call(ctx) for node in self.nodes]

class __extend__(New):
    def call(self, ctx=None):
        obj = W_Object()
        #it should be undefined... to be completed
        constructor = ctx.resolve_identifier(self.identifier).GetValue()
        obj.Put('prototype', constructor.Get('prototype'))
        constructor.Call(ctx, this = obj)
        
        return obj


class __extend__(Number):
    def call(self, ctx):
        return W_Number(self.num)
    
    def get_literal(self):
        return W_Number(self.num).ToString()

class __extend__(ObjectInit):
    def call(self, ctx):
        w_obj = W_Object()
        print "properties = ", self.properties
        for property in self.properties:
            name = property.name.get_literal()
            print "prop name = ", name
            w_expr = property.value.call(ctx).GetValue()
            w_obj.Put(name, w_expr)
        return w_obj

class __extend__(Plus):
    def call(self, ctx):
        print "left", self.left.call(ctx)
        left = self.left.call(ctx).GetValue()
        right = self.right.call(ctx).GetValue()
        prim_left = left.ToPrimitive('Number')
        prim_right = right.ToPrimitive('Number')
        # INSANE
        if isinstance(prim_left, W_String) or isinstance(prim_right, W_String):
            str_left = prim_left.ToString()
            str_right = prim_right.ToString()
            return W_String(str_left + str_right)
        else:
            num_left = prim_left.ToNumber()
            num_right = prim_right.ToNumber()
            # XXX: obey all the rules
            return W_Number(num_left + num_right)

class __extend__(Script):
    def call(self, ctx):
        for var in self.var_decl:
            ctx.variable.Put(var.name, w_Undefined)
                
        try:
            last = w_Undefined
            for node in self.nodes:
                last = node.call(ctx)
            return last
        except ExecutionReturned, e:
            return e.value

class __extend__(Semicolon):
    def call(self, ctx=None):
        return self.expr.call(ctx)

class __extend__(String):
    def call(self, ctx=None):
        return W_String(self.strval)
    
    def get_literal(self):
        return W_String(self.strval).ToString()

class __extend__(Return):
    def call(self, ctx):
        raise ExecutionReturned(self.expr.call(ctx))

class __extend__(Throw):
    def call(self, ctx):
        raise ThrowException(self.exception.call(ctx))

class __extend__(Try):
    def call(self, ctx):
        e = None
        try:
            tryresult = self.tryblock.call(ctx)
        except ThrowException, excpt:
            e = excpt
            if self.catchblock is not None:
                obj = W_Object()
                obj.Put(self.catchparam, e.exception)
                ctx.push_object(obj)
                tryresult = self.catchblock.call(ctx)
                ctx.pop_object()
        
        if self.finallyblock is not None:
            tryresult = self.finallyblock.call(ctx)
        
        #if there is no catchblock reraise the exception
        if (e is not None) and (self.catchblock is None):
            raise e
        
        return tryresult

class __extend__(Undefined):
    def call(self, ctx):
        return None

class __extend__(Vars):
    def call(self, ctx):
        print self.nodes
        for var in self.nodes:
            print var.name
            var.call(ctx)

class __extend__(While):
    def call(self, ctx):
        while self.condition.call(ctx).ToBoolean():
            self.body.call(ctx)

