"""tentative API for AOP in python.

heavily influenced by Aspect++"""

__all__ = ('around', 'before', 'after', 'introduce', 'PointCut', 'Aspect')
###########################
# API
###########################
import parser

# advices
# -------
class Advice(parser.ASTVisitor):
    requires_dynamic_pointcut=True
    def __init__(self, pointcut):
        if self.requires_dynamic_pointcut != pointcut.isdynamic:
            raise TypeError('Expecting a static pointcut')
        self.pointcut = pointcut
        dispatch = {ExecutionPointCut: self.weave_at_execution_pointcut,
                    CallPointCut: self.weave_at_call_pointcut,
                    InitializationPointCut: self.weave_at_initialization_pointcut,
                    DestructionPointCut: self.weave_at_destruction_pointcut,
                    PointCut: self.weave_at_static_pointcut,
                    }
        self.weave_at_pointcut = dispatch[pointcut.__class__]
                    
               
        
    def __call__(self, function):
        print 'wrapping advice %s on %s' % (self.pointcut, function.__name__)
        self.woven_code = function
        return self

    def weave(self, ast, enc):
        return ast.mutate(self)

    def default(self, node):
        if self.pointcut.match(node):
            node = self.weave_at_pointcut(node,
                                          self.pointcut.joinpoint(node))
        return node

##     def visitClass(self, node):
##         if self.pointcut.match(node):
##             print "found match", node.name
##         return node

    def weave_at_execution_pointcut(self, node, tjp):
        raise NotImplementedError("abstract method")
        
    def weave_at_call_pointcut(self, node, tjp):
        raise NotImplementedError("abstract method")
    
    def weave_at_initialization_pointcut(self, node, tjp):
        raise NotImplementedError("abstract method")
    
    def weave_at_destruction_pointcut(self, node, tjp):
        raise NotImplementedError("abstract method")
    
    def weave_at_static_pointcut(self, node, tjp):
        raise NotImplementedError("abstract method")

class around(Advice):
    """specify code to be run instead of the pointcut"""
    def weave_at_execution_pointcut(self, node, tjp):
        """weaving around a function execution moves the body of the
        function to an inner function called
        __aoptarget_<funcname>_<id>, and generate the following code:
        return __aop__(id, __aoptarget_<funcname>_<id>)
        """
        print"WEAVE around!!!"
        p = parser
        id = __aop__.register_joinpoint(self.woven_code, tjp)
        statement = node.code
        newname = '__aoptarget_%s_%s__' % (node.name, id)
        newcode = p.ASTStmt([p.ASTFunction(node.decorators,
                                           newname,
                                           node.argnames,
                                           node.defaults,
                                           node.flags,
                                           node.w_doc,
                                           node.code,
                                           node.lineno),                             
                             make_aop_call(id, targetname=newname,
                                           discard=False),
                             ])
        
        node.decorators = None
        node.code = newcode
        return node
    
    def weave_at_call_pointcut(self, node, tjp):
        raise NotImplementedError("abstract method")
    
    def weave_at_initialization_pointcut(self, node, tjp):
        raise NotImplementedError("abstract method")
    
    def weave_at_destruction_pointcut(self, node, tjp):
        raise NotImplementedError("abstract method")
    
class before(Advice):
    """specify code to be run before the pointcut"""
    def weave_at_execution_pointcut(self, node, tjp):
        """weaving before execution inserts a call to __aop__(id) at
        the beginning of the wrapped function definition"""
        print "WEAVE before!!!"
        id = __aop__.register_joinpoint(self.woven_code, tjp)
        statement_list = node.code.nodes
        statement_list.insert(0, make_aop_call(id))
        node.code.nodes = statement_list
        return node
        
    def weave_at_call_pointcut(self, node, tjp):
        """weaving before call replaces a call to foo(bar) with the
        following code:
        (lambda *args,**kwargs: (__aop__(id), foo(*args,**kwargs)))(bar)[1]
        """
        id = __aop__.register_joinpoint(self.woven_code, tjp)
        p = parser
        lambda_ret = p.ASTTuple((make_aop_call(id).expr, # we don't want the ASTDiscard
                                p.ASTCallFunc(node.node,
                                              [],
                                              p.ASTName('args'),
                                              p.ASTName('kwargs')))
                               )
        lambda_func = p.ASTLambda([p.ASTAssName('args', 0), p.ASTAssName('kwargs', 0)],
                                 [], # defaults
                                 p.CO_VARARGS | p.CO_VARKEYWORDS, 
                                 lambda_ret
                                 )
        call = p.ASTCallFunc(lambda_func,
                             node.args,
                             node.star_args,
                             node.dstar_args)
        newnode = p.ASTSubscript(call,
                                 p.OP_APPLY,
                                 p.ASTConst(1))
        print `newnode`
        return newnode
    
    def weave_at_initialization_pointcut(self, node, tjp):
        raise NotImplementedError("abstract method")
    
    def weave_at_destruction_pointcut(self, node, tjp):
        raise NotImplementedError("abstract method")
    
class after(Advice):
    """specify code to be run after the pointcut"""
    def weave_at_execution_pointcut(self, node, tjp):
        """weaving after execution wraps the code of the function in a
        try...finally block, and calls __aop__(id) in the finally
        block"""
        print "WEAVE after!!!"
        id = __aop__.register_joinpoint(self.woven_code, tjp)
        statement = node.code
        tryfinally = parser.ASTTryFinally(statement, make_aop_call(id))
        node.code = tryfinally
        return node

    def weave_at_call_pointcut(self, node, tjp):
        """weaving before call replaces a call to foo(bar) with the
        following code:
        (lambda *args,**kwargs: (foo(*args,**kwargs), __aop__(id)))(bar)[0]
        """
        id = __aop__.register_joinpoint(self.woven_code, tjp)
        p = parser
        lambda_ret = p.ASTTuple((p.ASTCallFunc(node.node,
                                              [],
                                              p.ASTName('args'),
                                              p.ASTName('kwargs')),
                                 make_aop_call(id).expr, # we don't want the ASTDiscard
                                )
                               )
        lambda_func = p.ASTLambda([p.ASTAssName('args', 0), p.ASTAssName('kwargs', 0)],
                                 [], # defaults
                                 p.CO_VARARGS | p.CO_VARKEYWORDS, 
                                 lambda_ret
                                 )
        call = p.ASTCallFunc(lambda_func,
                             node.args,
                             node.star_args,
                             node.dstar_args)
        newnode = p.ASTSubscript(call,
                                 p.OP_APPLY,
                                 p.ASTConst(0))
        print `newnode`
        return newnode
    
    
    def weave_at_initialization_pointcut(self, node, tjp):
        raise NotImplementedError("abstract method")
    
    def weave_at_destruction_pointcut(self, node, tjp):
        raise NotImplementedError("abstract method")
    
class introduce(Advice):
    """insert new code in the pointcut
    this is the only advice available on static point cuts"""
    requires_dynamic_pointcut=False
    def weave_at_pointcut(self, node, tjp):
        print "WEAVE introduce!!!"
        pass # XXX WRITEME
        return node

    
        
# JoinPoint
# --------

class JoinPoint:
    # API for use within advices
    def signature(self):
        """return: string representation of the signature of the joint
        point"""
        return self._signature

    def that(self):
        """return: a reference on the object initiating the call, or
        None if it is a static method or a global function"""
        return self._that
    
    def target(self):
        """return: reference the object that is the target of a call
        or None if it is a static method or a global function"""
        return self._target

    def result(self):
        """return: reference on result value or None"""
        return self._result

    def arguments(self):
        """return: the (args, kwargs) of the join point"""
        return self._arguments

    def proceed(self, *args, **kwargs):
        """execute the original code in an around advice"""
        self._result = self.func(*args, **kwargs)

    def action(self):
        """return: the runtime action object containing the execution
        environment to execute XXX"""
        pass

    def __init__(self, signature=None, that=None, target=None, result=None, arguments=None, func=None):
        self._signature = signature
        self._that = that
        self._target = target
        self._result = result
        if arguments is None:
            arguments = (), {}
        self._arguments = arguments
        self._argnames = None
        self.func = func
    

# PointCut
# --------

class PointCut:
    """a collection of Join Points."""
    # maybe not managed as a real collection.
    
    # API for use in declarative code
    def __init__(self, pointcut):
        """if pointcut is a string:
               * matches a substring without . or ,
               ** matches any substring
               pointcut looks like object_name_or_pattern[([argname_or_pattern[, ...]])]
               the pointcut is static
           else, pointcut must be a pointcut instance"""
        if type(pointcut) == str:
            self.pointcutdef = pointcut
        elif isinstance(pointcut, PointCut):
            self.pointcutdef = pointcut.pointcutdef # XXX FIXME
        else:
            raise TypeError(type(pointcut))
        self.isdynamic = False

    def __and__(self, other):
        """return: new pointcut, intersection of the join points in the self and other"""
        pass
    def __or__(self, other):
        """return: new pointcut, union of the join points in the self and other"""
        pass
    def __not__(self):
        """return: new pointcut, exclusion of the join points in self"""
        pass

    def call(self):
        """return a dynamic pointcut representing places where the pointcut is called"""
        return CallPointCut(self)

    def execution(self):
        """return a dynamic pointcut representing places where the pointcut is executed"""
        return ExecutionPointCut(self)

    def initialization(self):
        """return a dynamic pointcut representing places where the pointcut is instantiated"""
        return InitializationPointCut(self)
    
    def destruction(self):
        """return a dynamic pointcut representing places where the pointcut is destroyed"""
        return DestructionPointCut(self)
    
    def match(self, astnode):
        raise NotImplementedError
    
    def joinpoint(self, node):
        """returns a join point instance for the node"""
        assert self.match(node)
        return JoinPoint()


class AbstractDynamicPointCut(PointCut):
    def __init__(self, pointcut):
        PointCut.__init__(self, pointcut)
        self.isdynamic = True

        
class ExecutionPointCut(AbstractDynamicPointCut):
    def match(self, astnode):
        return isinstance(astnode, parser.ASTFunction) and astnode.name == self.pointcutdef

    def joinpoint(self, node):
        """returns a join point instance for the node"""
        assert self.match(node)
        jp = JoinPoint()
        jp._flags = node.flags
        jp._argnames = [a.name for a in node.argnames]
        jp._defaultargvalues = [d.value for d in node.defaults]
        
        return jp

class CallPointCut(AbstractDynamicPointCut):
    def match(self, node):
        return isinstance(node, parser.ASTCallFunc) and isinstance(node.node, parser.ASTName) and node.node.varname == self.pointcutdef

class DestructionPointCut(AbstractDynamicPointCut):
    pass

class InitializationPointCut(AbstractDynamicPointCut):
    pass


### make these class methods of PointCut ?
def within(pointcutstring):
    """return point cut filtering  joinpoints on lexical scope"""
    pass

def base(pointcutstring):
    """return class pointcuts based on the class hierarchy"""
    pass
def derived(pointcutstring):
    """return class pointcuts based on the class hierarchy"""
    pass

def that(typepattern):
    pass
def target(typepattern):
    pass
def result(typepattern):
    pass
def args(typepattern):
    pass


class Weaver:
    """The weaver is responsible for weaving the Aspects in the code
    using the compiler_hook. The woven modules will generally use the
    __aop__ builtin instance of this class to run the advices"""
    def __init__(self):
        self.advices = []
        self.joinpoints = {}
        self._id = 1
        parser.install_compiler_hook(self.weave)

    def register_advice(self, aspect, advice):
        self.advices.append((aspect, advice))

    def weave(self, ast, enc):
        for aspect, advice in self.advices:
            self._curr_aspect = aspect
            ast = advice.weave(ast, enc)
        self._curr_aspect = None
        return ast

    def _clear_all(self):
        self.advices = []
        self.joinpoints = {}

    def _next_id(self):
        try:
            return self._id
        finally:
            self._id += 1
    
    def register_joinpoint(self, woven_code, joinpoint,  *args):
        assert self._curr_aspect is not None
        id = self._next_id()
        print "register joinpoint with id %d" % id
        arguments = self._curr_aspect, joinpoint, args
        self.joinpoints[id] = woven_code, arguments
        return id

    def __call__(self, id, target=None, target_locals = None):
        woven_code, (aspect, joinpoint, arguments) = self.joinpoints[id]
        joinpoint.func = target
        print 'target_locals', target_locals
        if target_locals is not None:
            joinpoint._arguments = (), dict([(n, target_locals[n]) for n in joinpoint._argnames or ()])
        args = (aspect, joinpoint,) + arguments
        return woven_code(*args)

import __builtin__
__builtin__.__aop__ = Weaver()
del __builtin__



# Aspect metaclass
# ----------------

class Aspect(type):
##     def __init__(cls, name, bases, dct):
##         super(Aspect, cls).__init__(name, bases, dct)

    def __call__(cls, *args, **kwargs):
        instance = super(Aspect, cls).__call__(*args, **kwargs)
        for name, advice in cls.__dict__.iteritems():
            if isinstance(advice, Advice):
                print "registering advice %s.%s" % (instance.__class__.__name__, name)
                __aop__.register_advice(instance, advice)

        return instance

# helper functions 
def make_aop_call(id, targetname=None, discard=True):
    """return an AST for a call to a woven function
    id is the integer returned when the advice was stored in the registry"""
    p = parser
    arguments = [p.ASTConst(id),]
    if targetname is not None:
        arguments.append(p.ASTName(targetname))
    else:
        arguments.append(p.ASTName('None'))
    arguments.append(p.ASTCallFunc(p.ASTName('locals'),
                                   [], None, None)
                     )
                         
    if discard:
        returnclass = p.ASTDiscard
    else:
        returnclass = p.ASTReturn
    return returnclass(p.ASTCallFunc(p.ASTName('__aop__'),
                                      arguments,
                                      None, # *args
                                      None # *kwargs
                                      )
                        )

# debugging visitor
class Debug(parser.ASTVisitor):
    def __init__(self):
        self.offset = 0
    def default(self, node):
        print ' '*self.offset+str(node)
        self.offset += 4
        for child in node.getChildNodes():
            child.accept(self)
        self.offset -= 4
        return node

    

DEBUGGER= Debug()
