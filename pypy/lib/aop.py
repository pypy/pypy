"""tentative API for AOP in python.

heavily influenced by Aspect++"""


###########################
# API
###########################
import parser

# advices
# -------


class Debug(parser.ASTVisitor):
    def __init__(self):
        self.offset = 0
    def default(self, node):
        print ' '*self.offset+str(node)
        self.offset += 2
        for child in node.getChildNodes():
            child.accept(self)
        self.offset -= 2
        return node

DEBUGGER= Debug()

class Advice(parser.ASTVisitor):
    requires_dynamic_pointcut=True
    def __init__(self, pointcut):
        if self.requires_dynamic_pointcut != pointcut.isdynamic:
            raise TypeError('Expecting a static pointcut')
        self.pointcut = pointcut
        
    def __call__(self, function):
        print 'wrapping advice %s on %s' % (self.pointcut, function.__name__)
        self.function = function
        return self

##     def decorated(self,*args, **kwargs):
##         print 'calling aspectized function %s (with %s)' % (self.function.__name__, self.pointcut)
##         return self.function(*args, **kwargs)

    def weave(self, ast, enc):
        return ast.accept(self)

    def visitFunction(self, node):
        if self.pointcut.match(node):
            self.weave_at_pointcut(node,
                                   self.pointcut.joinpoint(node))
        return node

    def vistClass(self, node):
        if self.pointcut.match(node):
            print "found match", node.name
        return node
        

def make_aop_call(id):
    """return an AST for a call to a woven function
    id is the integer returned when the advice was stored in the registry"""
    p = parser
    return p.ASTDiscard(p.ASTCallFunc(p.ASTName('__aop__'),
                                      [p.ASTConst(id),], # arguments
                                      None, # *args
                                      None # *kwargs
                                      )
                        )
                     

def is_aop_call(node):
    p = parser
    return node.__class__ == p.ASTDiscard and \
           node.expr.__class__ == p.ASTCallFunc and \
           node.expr.node.varname == '__aop__'

class around(Advice):
    """specify code to be run instead of the pointcut"""
    def weave_at_pointcut(self, node, tjp):
        print "WEAVE around!!!"
        pass # XXX WRITEME

class before(Advice):
    """specify code to be run before the pointcut"""
    def weave_at_pointcut(self, node, tjp):
        print "WEAVE before!!!"
        id = __aop__.register_joinpoint(self.function, tjp)
        statement_list = node.code.nodes
        for idx, stmt in enumerate(statement_list):
            if is_aop_call(stmt):
                continue
            else:
                break
        statement_list.insert(idx, make_aop_call(id))
        node.code.nodes = statement_list
        
            

class after(Advice):
    """specify code to be run after the pointcut"""
    def weave_at_pointcut(self, node, tjp):
        print "WEAVE after!!!"
        pass # XXX WRITEME

class introduce(Advice):
    """insert new code in the pointcut
    this is the only advice available on static point cuts"""
    requires_dynamic_pointcut=False
    def weave_at_pointcut(self, node, tjp):
        print "WEAVE introduce!!!"
        pass # XXX WRITEME

    
        
# TODO: add new base classes to a pointcut. Maybe with introduce ?

# JoinPoint
# --------

class JoinPoint:
    # API for use within advices
    def signature(self):
        """return: string representation of the signature of the joint
        point"""
        return self.signature

    def that(self):
        """return: a reference on the object initiating the call, or
        None if it is a static method or a global function"""
        return self.that
    
    def target(self):
        """return: reference the object that is the target of a call
        or None if it is a static method or a global function"""
        return self.target

    def result(self):
        """return: reference on result value or None"""
        return self.result

    def arguments(self):
        """return: the (args, kwargs) of the join point"""
        return self.arguments

    def proceed(self, *args, **kwargs):
        """execute the original code in an around advice"""
        self.result = self.func(*args, **kwargs)

    def action(self):
        """return: the runtime action object containing the execution
        environment to execute XXX"""
        pass

    def __init__(self, signature=None, that=None, target=None, result=None, arguments=None, func=None):
        self.signature = signature
        self.that = that
        self.target = target
        self.result = result
        self.arguments = arguments
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
        # XXX may be difficult to implement ?
        self.isdynamic = True
        #raise NotImplementedError('call')
        return self

    def execution(self):
        """return a dynamic pointcut representing places where the pointcut is executed"""
        self.isdynamic = True
        return self

    def initialization(self):
        """return a dynamic pointcut representing places where the pointcut is instantiated"""
        self.isdynamic = True
        #raise NotImplementedError('initialization')
        return self
    
    def destruction(self):
        """return a dynamic pointcut representing places where the pointcut is destroyed"""
        self.isdynamic = True
        #raise NotImplementedError('destruction')

        return self

    def match(self, astnode):
        # FIXME !!! :-)
        try:
            return astnode.name == self.pointcutdef
        except AttributeError:
            return False

    def joinpoint(self, node):
        """returns a join point instance for the node"""
        assert self.match(node)
        return JoinPoint()

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

    def _next_id(self):
        try:
            return self._id
        finally:
            self._id += 1
    
    def register_joinpoint(self, callable, *args):
        assert self._curr_aspect is not None
        id = self._next_id()
        args = (self._curr_aspect,) + args
        self.joinpoints[id] = callable, args
        return id

    def __call__(self, id):
        callable, args = self.joinpoints[id]
        callable(*args)

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


