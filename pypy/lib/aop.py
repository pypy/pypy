"""tentative API for AOP in python.

heavily influenced by Aspect++"""


__all__ = ('around', 'before', 'after', 'introduce', 'PointCut', 'Aspect')
###########################
# API
###########################
import parser
import re
import sys
import os
import os.path as osp

# advices
# -------
class Advice(parser.ASTMutator):
    requires_dynamic_pointcut=True
    def __init__(self, pointcut):
        if self.requires_dynamic_pointcut != pointcut.isdynamic:
            raise TypeError('Expecting a static pointcut')
        self.pointcut = pointcut
        dispatch = {ExecutionPointCut: self.weave_at_execution,
                    CallPointCut: self.weave_at_call,
                    InitializationPointCut: self.weave_at_initialization,
                    DestructionPointCut: self.weave_at_destruction,
                    PointCut: self.weave_at_static,
                    }
        self.weave_at = dispatch[pointcut.__class__]
        self.woven_code = None
                    
               
    def __repr__(self):
        return '<%s: %s at %s>' % (self.__class__.__name__,
                                   self.woven_code,
                                   self.pointcut)
        
    def __call__(self, function):
        self.woven_code = function
        return self

    def weave(self, ast, enc, modulename):
        self.curr_encoding = enc
        if self.pointcut.match_module(modulename):
            return ast.mutate(self)
        else:
            return ast

    def default(self, node):
        if self.pointcut.match(node):
            node = self.weave_at(node,
                                 self.pointcut.joinpoint(node))
        return node

    def weave_at_execution(self, node, tjp):
        raise NotImplementedError("abstract method")
        
    def weave_at_call(self, node, tjp):
        raise NotImplementedError("abstract method")
    
    def weave_at_initialization(self, node, tjp):
        raise NotImplementedError("abstract method")
    
    def weave_at_destruction(self, node, tjp):
        raise NotImplementedError("abstract method")
    
    def weave_at_static(self, node, tjp):
        raise NotImplementedError("abstract method")


class around(Advice):
    """specify code to be run instead of the pointcut"""
    def weave_at_execution(self, node, tjp):
        """weaving around a function execution moves the body of the
        function to an inner function called
        __aoptarget_<id>__, and generate the following code:
        return __aop__(id, __aoptarget_<id>__)
        """
        p = parser
        id = __aop__.register_joinpoint(self.woven_code, tjp)
        statement = node.code
        newname = '__aoptarget_%s__' % (id)
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
    
    def weave_at_call(self, node, tjp):
        p = parser
        id = __aop__.register_joinpoint(self.woven_code, tjp)
        newnode = make_aop_call_for_around_call(id,
                                                node.node.varname,
                                                node.args,
                                                node.star_args,
                                                node.dstar_args
                                                )
        return newnode
    
    def weave_at_initialization(self, node, tjp):
        raise NotImplementedError("abstract method")
    
    def weave_at_destruction(self, node, tjp):
        raise NotImplementedError("abstract method")
    
class before(Advice):
    """specify code to be run before the pointcut"""
    def weave_at_execution(self, node, tjp):
        """weaving before execution inserts a call to __aop__(id) at
        the beginning of the wrapped function definition"""
        id = __aop__.register_joinpoint(self.woven_code, tjp)
        statement_list = node.code.nodes
        statement_list.insert(0, make_aop_call(id))
        node.code.nodes = statement_list
        return node
        
    def weave_at_call(self, node, tjp):
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
        return newnode
    
    def weave_at_initialization(self, node, tjp):
        raise NotImplementedError("abstract method")
    
    def weave_at_destruction(self, node, tjp):
        raise NotImplementedError("abstract method")
    
class after(Advice):
    """specify code to be run after the pointcut"""
    def weave_at_execution(self, node, tjp):
        """weaving after execution wraps the code of the function in a
        try...finally block, and calls __aop__(id) in the finally
        block"""
        id = __aop__.register_joinpoint(self.woven_code, tjp)
        statement = node.code
        tryfinally = parser.ASTTryFinally(statement, make_aop_call(id))
        node.code = tryfinally
        return node

    def weave_at_call(self, node, tjp):
        """weaving before call replaces a call to foo(bar) with the
        following code:
        __aop__(id, result=foo(bar)) 
        """
        id = __aop__.register_joinpoint(self.woven_code, tjp)
        p = parser
        newnode = make_aop_call(id, resultcallfuncnode=node).expr # we don't want the ASTDiscard
        return newnode
    
    
    def weave_at_initialization(self, node, tjp):
        raise NotImplementedError("abstract method")
    
    def weave_at_destruction(self, node, tjp):
        raise NotImplementedError("abstract method")
    
class introduce(Advice):
    """insert new code in the pointcut
    this is the only advice available on static point cuts"""
    requires_dynamic_pointcut=False
    def weave_at_static(self, node, tjp):
        p = parser
        id = __aop__.register_joinpoint(self.woven_code, tjp)
        if node.code.__class__ == p.ASTPass:
            node.code = p.ASTStmt([])
            
        methods = node.code.nodes

        newmethod = p.ASTFunction(None,
                                  self.woven_code.func_name,
                                  [p.ASTAssName('self', 0),
                                   p.ASTAssName('args', 0),
                                   ],
                                  [],
                                  p.CO_VARARGS, 
                                  self.woven_code.func_doc,
                                  p.ASTStmt([p.ASTPrintnl([p.ASTName('self')], None),
                                             p.ASTPrintnl([p.ASTName('args')], None),
                                             p.ASTReturn(p.ASTCallFunc(p.ASTGetattr(p.ASTName('__aop__'), 'call_introduced'),
                                                                       [p.ASTConst(id),
                                                                        p.ASTAdd(p.ASTTuple([p.ASTName('self')]), p.ASTName('args')),
                                                                        ], None, None)
                                                         )
                                             ]
                                            ),
                                  node.lineno
                                  )
        
        
        
        methods.append(newmethod)
        node.code.nodes = methods
        return node

    
        
# JoinPoint
# --------
class JoinPoint:
    # API for use within advices
    def signature(self):
        """return: string representation of the signature of the joint
        point"""
        return self._signature

    def name(self):
        return self._name

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
        self._name = None
    

# PointCut
# --------

class PointCut:
    """a collection of Join Points."""
    # maybe not managed as a real collection.
    
    # API for use in declarative code
    def __init__(self, module=".*", klass=".*", func=".*", pointcut=None):
        """If pointcut is not None, it is assumed to be a PointCut
        instance and will be used to get the filters.  Otherwise, the
        module, klass and func arguments are used as regular
        expressions which will be used against the modulename,
        classname and function/method name for the pointcut
        
        The created point cut is static. 

        The pointcut argument can also be a pointcut instance"""
        if pointcut is None:
            self.func_re = re.compile(func)
            self.module_re = re.compile(module)
            self.class_re = re.compile(klass)
        elif isinstance(pointcut, PointCut):
            self.func_re = pointcut.func_re
            self.module_re = pointcut.module_re
            self.class_re = pointcut.class_re
        else:
            raise TypeError(type(pointcut))
        self.isdynamic = False

    def __repr__(self):
        return '<%s on %s:%s:%s>' % (self.__class__.__name__,
                                     self.module_re.pattern,
                                     self.class_re.pattern,
                                     self.func_re.pattern)

    def __and__(self, other):
        """return: new pointcut, intersection of the join points in the self and other"""
        if not isinstance(other, PointCut):
            raise TypeError(other.__class__.__name__)
        return _AndPC(self, other)
    
    def __or__(self, other):
        """return: new pointcut, union of the join points in the self and other"""
        if not isinstance(other, PointCut):
            raise TypeError(other.__class__.__name__)
        return _OrPC(self, other)
    
##     def __not__(self):
##         """return: new pointcut, exclusion of the join points in self"""
##         pass
    
    # Dynamic pointcut creation
    def call(self):
        """return a dynamic pointcut representing places where the pointcut is called"""
        return CallPointCut(pointcut=self)

    def execution(self):
        """return a dynamic pointcut representing places where the pointcut is executed"""
        return ExecutionPointCut(pointcut=self)

    def initialization(self):
        """return a dynamic pointcut representing places where the pointcut is instantiated"""
        assert self.func_re.pattern == '.*'
        return InitializationPointCut(pointcut=self)
    
    def destruction(self):
        """return a dynamic pointcut representing places where the pointcut is destroyed"""
        assert self.func_re.pattern == '.*'
        return DestructionPointCut(pointcut=self)

    # API for use during the Weaving process
    def match_module(self, modulename):
        return self.module_re.match(modulename)

    def find_classname(self, node):
        while node is not None:
            node = node.parent
            if isinstance(node, parser.ASTClass):
                return node.name
        return ''
            
    def match(self, node):
        "a static point cut only matches classes: the function part is not used"
        assert self.func_re.pattern == '.*'
        return isinstance(node, parser.ASTClass) and \
               self.class_re.match(node.name)
        
    def joinpoint(self, node):
        """returns a join point instance for the node"""
#        assert self.match(node)
        return JoinPoint()

class _CompoundPC(PointCut):
    def __init__(self, pc1, pc2):
        self.pc1 = pc1
        self.pc2 = pc2

    def __repr__(self):
        return "<%s(%r, %r)>" % (self.__class__.__name__, self.pc1, self.pc2)
    def call(self):
        """return a dynamic pointcut representing places where the pointcut is called"""
        return self.__class__(self.pc1.call(), self.pc2.call())

    def execution(self):
        """return a dynamic pointcut representing places where the pointcut is executed"""
        return self.__class__(self.pc1.execution(), self.pc2.execution())

    def initialization(self):
        """return a dynamic pointcut representing places where the pointcut is instantiated"""
        return self.__class__(self.pc1.initialization(), self.pc2.initialization())
    
    def destruction(self):
        """return a dynamic pointcut representing places where the pointcut is destroyed"""
        return self.__class__(self.pc1.destruction(), self.pc2.destruction())

class _AndPC(_CompoundPC):
    def match_module(self, modulename):
        return self.pc1.match_module(modulename) and self.pc2.match_module(modulename)

    def match(self, node):
        return self.pc1.match(node) and self.pc2.match(node)

class _OrPC(_CompoundPC):
    def __init__(self, pc1, pc2):
        self.pc1 = pc1
        self.pc2 = pc2
        
    def match_module(self, modulename):
        return self.pc1.match_module(modulename) or self.pc2.match_module(modulename)

    def match(self, node):
        return self.pc1.match(node) or self.pc2.match(node)

class AbstractDynamicPointCut(PointCut):
    def __init__(self, pointcut):
        PointCut.__init__(self, pointcut=pointcut)
        self.isdynamic = True

    # call, execution, initialization and destruction are disallowed
    # on dynamic pointcuts
    def call(self):
        raise TypeError(self.__class__.__name__)

    def execution(self):
        raise TypeError(self.__class__.__name__)

    def initialization(self):
        raise TypeError(self.__class__.__name__)
    
    def destruction(self):
        raise TypeError(self.__class__.__name__)
        
class ExecutionPointCut(AbstractDynamicPointCut):
    """An execution point cut matches the execution of a function
    matching func_re, defined within a class matching class_re written
    in a module matching module_re"""

    def match(self, node):
        if not isinstance(node, parser.ASTFunction):
            return False
        classname = self.find_classname(node)
        return self.class_re.match(classname) and \
               self.func_re.match(node.name)

    def joinpoint(self, node):
        """returns a join point instance for the node"""
#        assert self.match(node)
        jp = JoinPoint()
        jp._name = node.name
        jp._flags = node.flags
        jp._argnames = [a.name for a in node.argnames]
        jp._defaultargvalues = [d.value for d in node.defaults]
        
        return jp

class CallPointCut(AbstractDynamicPointCut):
    """A call point cut matches a call to a function or method
    matching func_re, within a class matching class_re written in a
    module matching module_re"""

    def match(self, node):
        if not isinstance(node, parser.ASTCallFunc):
            return False
        classname = self.find_classname(node)
        return isinstance(node, parser.ASTCallFunc) and \
               isinstance(node.node, parser.ASTName) and \
               self.class_re.match(classname) and \
               self.func_re.match(node.node.varname)


### XXX: won't match anything if no __del__ method exists (or only on a parent class)
class DestructionPointCut(ExecutionPointCut):
    """A destruction pointcut matches the execution of a __del__
    method in a class matching class_re in a module matching module_re"""
    def __init__(self, pointcut):
        ExecutionPointCut.__init__(self, pointcut=pointcut)
        self.func_re = re.compile('^__del__$')

### XXX: won't match anything if no __init__ method exists (or only on a parent class)
class InitializationPointCut(ExecutionPointCut):
    """An initialization point cut matches the execution of the
    __init__ method of a class matching class_re in a module matching
    module_re""" 
    def __init__(self, pointcut):
        ExecutionPointCut.__init__(self, pointcut=pointcut)
        self.func_re = re.compile('^__init__$')

class _UndefinedResult:
    """used to denote that the result of a call to a aspectised
    function is not known"""
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

    def _guessmodule(self, filename):
        for p in sys.path:
            cp = osp.commonprefix([p, filename])
            if osp.isdir(cp):
                break
        else:
            cp = ''
        guessed = osp.splitext(filename[len(cp):])[0].replace(os.sep, '.')
        if guessed.startswith('.'):
            guessed = guessed[1:]
        if guessed.endswith('.__init__'):
            guessed = guessed[:-9]
        return guessed
        

    def weave(self, ast, enc, filename):
        if not self.advices:
            return ast
        try:
            modulename = self._guessmodule(filename)
            for aspect, advice in self.advices:
                self._curr_aspect = aspect
                ast = advice.weave(ast, enc, modulename)
            self._curr_aspect = None
            return ast
        except Exception, exc:
            error('%s: %s in weave', exc.__class__.__name__, exc)
            return ast
    def _clear_all(self):
        self.advices = []
        self.joinpoints = {}

    def _next_id(self):
        try:
            return self._id
        finally:
            self._id += 1
    
    def register_joinpoint(self, woven_code, joinpoint,  *args): # FIXME: do we need *args ?
        assert self._curr_aspect is not None
        id = self._next_id()
        arguments = self._curr_aspect, joinpoint, args
        self.joinpoints[id] = woven_code, arguments
        return id

    def __call__(self, id, target=None, target_locals = None, result=_UndefinedResult):
        woven_code, (aspect, joinpoint, arguments) = self.joinpoints[id]
        joinpoint.func = target
        if type(target_locals) is dict: 
            joinpoint._arguments = (), dict([(n, target_locals[n]) for n in joinpoint._argnames or () if n != 'self'])
            if 'self' in target_locals:
                joinpoint._target = target_locals['self']
        elif type(target_locals) is tuple:
            joinpoint._arguments = target_locals, {}
        if result is not _UndefinedResult:
            joinpoint._result = result
        args = (aspect, joinpoint,) + arguments
        return woven_code(*args)

    def call_introduced(self, id, args):
        woven_code, (aspect, joinpoint, arguments) = self.joinpoints[id]
        return woven_code(aspect, *args)
        

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
                __aop__.register_advice(instance, advice)

        return instance

# helper functions 
def make_aop_call(id, targetname=None, discard=True, resultcallfuncnode=None):
    """return an AST for a call to a woven function
    
    id is the integer returned when the advice was stored in the
    registry

    targetname is the name of the function that will be run when
    jointpoint.proceed() is called by the advice

    if discard is True, the call is wrapped in an ASTDiscard node,
    otherwise an ASTReturn node is used

    If resultcallfuncnode is not None, it is expected to be an
    ASTCallFunc node which will be inserted as an argument in the aop
    call, so that the function is called and its return value is
    passed to the __aop__ instance.
    """
    p = parser
    arguments = [p.ASTConst(id),]
    if targetname is not None:
        arguments.append(p.ASTName(targetname))
    else:
        arguments.append(p.ASTName('None'))
    
    arguments.append(p.ASTCallFunc(p.ASTName('locals'),
                                   [], None, None)
                     )
                         
    if resultcallfuncnode is not None:
        arguments.append(resultcallfuncnode)

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
def make_aop_call_for_around_call(id, targetname, target_args, target_starargs, target_dstar_args):
    """return an AST for a call to a woven function
    
    id is the integer returned when the advice was stored in the
    registry

    targetname is the name of the function that will be run when
    jointpoint.proceed() is called by the advice

    target_args, target_starargs, target_dstar_args are the values of the original ASTCallFunc 
    """
    p = parser
    arguments = [p.ASTConst(id),]
    if targetname is not None:
        arguments.append(p.ASTName(targetname))
    else:
        arguments.append(p.ASTName('None'))

    callargs = [p.ASTList(target_args)]        
    
    arguments.append(p.ASTTuple(callargs))
                                              
    return p.ASTCallFunc(p.ASTName('__aop__'),
                         arguments,
                         None, # *args
                         None # *kwargs
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
