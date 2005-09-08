"""Generate ast module from specification

This script generates the ast module from a simple specification,
which makes it easy to accomodate changes in the grammar.  This
approach would be quite reasonable if the grammar changed often.
Instead, it is rather complex to generate the appropriate code.  And
the Node interface has changed more often than the grammar.
"""
# This is a slightly modified version from the original that adds a
# visit method to each node

import fileinput
import getopt
import re
import sys
from StringIO import StringIO

SPEC = "ast.txt"
COMMA = ", "

def load_boilerplate(file):
    f = open(file)
    buf = f.read()
    f.close()
    i = buf.find('### ''PROLOGUE')
    j = buf.find('### ''EPILOGUE')
    pro = buf[i+12:j].strip()
    epi = buf[j+12:].strip()
    return pro, epi

def strip_default(arg):
    """Return the argname from an 'arg = default' string"""
    i = arg.find('=')
    if i == -1:
        return arg
    t = arg[:i].strip()
    return t

P_NODE = 1
P_OTHER = 2
P_NESTED = 3
P_NONE = 4

class NodeInfo:
    """Each instance describes a specific AST node"""
    def __init__(self, name, args, parent=None):
        self.name = name
        self.args = args.strip()
        self.argnames = self.get_argnames()
        self.argprops = self.get_argprops()
        self.nargs = len(self.argnames)
        self.init = []
        self.flatten_nodes = {}
        self.additional_methods = {}
        self.parent = parent

    def setup_parent(self, classes):
        if self.parent:
            self.parent = classes[self.parent]
        else:
            self.parent = NodeInfo("Node","")

    def get_argnames(self):
        if '(' in self.args:
            i = self.args.find('(')
            j = self.args.rfind(')')
            args = self.args[i+1:j]
        else:
            args = self.args
        return [strip_default(arg.strip())
                for arg in args.split(',') if arg]

    def get_argprops(self):
        """Each argument can have a property like '*' or '!'

        XXX This method modifies the argnames in place!
        """
        d = {}
        hardest_arg = P_NODE
        for i in range(len(self.argnames)):
            arg = self.argnames[i]
            if arg.endswith('*'):
                arg = self.argnames[i] = arg[:-1]
                d[arg] = P_OTHER
                hardest_arg = max(hardest_arg, P_OTHER)
            elif arg.endswith('!'):
                arg = self.argnames[i] = arg[:-1]
                d[arg] = P_NESTED
                hardest_arg = max(hardest_arg, P_NESTED)
            elif arg.endswith('&'):
                arg = self.argnames[i] = arg[:-1]
                d[arg] = P_NONE
                hardest_arg = max(hardest_arg, P_NONE)
            else:
                d[arg] = P_NODE
        self.hardest_arg = hardest_arg

        if hardest_arg > P_NODE:
            self.args = self.args.replace('*', '')
            self.args = self.args.replace('!', '')
            self.args = self.args.replace('&', '')

        return d

    def gen_source(self):
        buf = StringIO()
        print >> buf, "class %s(%s):" % (self.name, self.parent.name)
        self._gen_init(buf)
        print >> buf
        self._gen_getChildren(buf)
        print >> buf
        self._gen_getChildNodes(buf)
        print >> buf
        self._gen_additional_methods(buf)
        self._gen_repr(buf)
        print >> buf
        self._gen_visit(buf)
        buf.seek(0, 0)
        return buf.read()

    def _gen_init(self, buf):
        if self.parent.args and self.args:
            args = self.parent.args +","+ self.args
        else:
            args = self.parent.args or self.args
        if args:
            print >> buf, "    def __init__(self, %s, lineno=-1):" % args
        else:
            print >> buf, "    def __init__(self, lineno=-1):"
        if self.parent.args:
            print >> buf, "        %s.__init__(self, %s, lineno)" % self.parent.args
        else:
            print >> buf, "        Node.__init__(self, lineno)"
        if self.argnames:
            for name in self.argnames:
                if name in self.flatten_nodes:
                    print >>buf, "    %s" % self.flatten_nodes[name][0].rstrip()
                print >> buf, "        self.%s = %s" % (name, name)
        if self.init:
            print >> buf, "".join(["    " + line for line in self.init])

    def _gen_getChildren(self, buf):
        print >> buf, "    def getChildren(self):"
        print >> buf, '        "NOT_RPYTHON"'        
        if len(self.argnames) == 0:
            print >> buf, "        return []"
        else:
            if self.hardest_arg < P_NESTED:
                clist = COMMA.join(["self.%s" % c
                                    for c in self.argnames])
                if self.nargs == 1:
                    print >> buf, "        return %s," % clist
                else:
                    print >> buf, "        return %s" % clist
            else:
                if len(self.argnames) == 1:
                    print >> buf, "        return tuple(flatten(self.%s))" % self.argnames[0]
                else:
                    print >> buf, "        children = []"
                    template = "        children.%s(%sself.%s%s)"
                    for name in self.argnames:
                        if self.argprops[name] == P_NESTED:
                            print >> buf, template % ("extend", "flatten(",
                                                      name, ")")
                        else:
                            print >> buf, template % ("append", "", name, "")
                    print >> buf, "        return tuple(children)"

    def _gen_getChildNodes(self, buf):
        print >> buf, "    def getChildNodes(self):"
        if len(self.argnames) == 0:
            print >> buf, "        return []"
        else:
            if self.hardest_arg < P_NESTED:
                clist = ["self.%s" % c
                         for c in self.argnames
                         if self.argprops[c] == P_NODE]
                if len(clist) == 0:
                    print >> buf, "        return []"
                elif len(clist) == 1:
                    print >> buf, "        return [%s,]" % clist[0]
                else:
                    print >> buf, "        return [%s]" % COMMA.join(clist)
            else:
                print >> buf, "        nodelist = []"
                template = "        nodelist.%s(%sself.%s%s)"
                for name in self.argnames:
                    if self.argprops[name] == P_NONE:
                        tmp = ("        if self.%s is not None:\n"
                               "            nodelist.append(self.%s)")
                        print >> buf, tmp % (name, name)
                    elif self.argprops[name] == P_NESTED:
                        if name not in self.flatten_nodes:
                            print >> buf, template % ("extend", "",
                                                      name, "")
                        else:
                            flat_logic = self.flatten_nodes[name]
                            while not flat_logic[-1].strip():
                                flat_logic.pop()
                            flat_logic[-1] = flat_logic[-1].rstrip()
                            print >> buf, "".join(["    " + line for line in flat_logic])
                    elif self.argprops[name] == P_NODE:
                        print >> buf, template % ("append", "", name, "")
                print >> buf, "        return nodelist"

    def _gen_repr(self, buf):
        print >> buf, "    def __repr__(self):"
        if self.argnames:
            fmt = COMMA.join(["%s"] * self.nargs)
            if '(' in self.args:
                fmt = '(%s)' % fmt
            vals = ["repr(self.%s)" % name for name in self.argnames]
            vals = COMMA.join(vals)
            if self.nargs == 1:
                vals = vals + ","
            print >> buf, '        return "%s(%s)" %% (%s)' % \
                  (self.name, fmt, vals)
        else:
            print >> buf, '        return "%s()"' % self.name

    def _gen_visit(self, buf):
        print >> buf, "    def accept(self, visitor):"
        print >> buf, "        return visitor.visit%s(self)" % self.name

    def _gen_additional_methods(self, buf):
        for key, value in self.additional_methods.iteritems():
            if key not in '_cur_':
                print >> buf, ''.join(value)
                # print >> buf, '\n\n'
            
    def gen_base_visit(self, buf):
        print >> buf, "    def visit%s(self, node):" % self.name
        print >> buf, "        return self.default( node )"

rx_init = re.compile('init\((.*)\):')
rx_flatten_nodes = re.compile('flatten_nodes\((.*)\.(.*)\):')
rx_additional_methods = re.compile('(.*)\.(.*)\((.*?)\):')

def parse_spec(file):
    classes = {}
    cur = None
    kind = None
    for line in fileinput.input(file):
        mo = None
        comment = line.strip().startswith('#')
        if not comment:
            mo = rx_init.search(line)
            if mo:
                kind = 'init'
            else:
                mo = rx_flatten_nodes.search(line)
                if mo:
                    kind = 'flatten_nodes'
                else:
                    mo = rx_additional_methods.search(line)
                    if mo:
                        kind = 'additional_method'
        if mo is None:
            if cur is None:
                if comment:
                    continue
                # a normal entry
                try:
                    name, args = line.split(':')
                except ValueError:
                    continue
                if "(" in name:
                    name, parent = name.split("(")
                    parent = parent[:-1]
                else:
                    parent = None
                classes[name] = NodeInfo(name, args, parent)
                cur = None
            elif kind == 'init':
                # some code for the __init__ method
                cur.init.append(line)
            elif kind == 'flatten_nodes':
                cur.flatten_nodes['_cur_'].append(line)
            elif kind == 'additional_method':
                cur.additional_methods['_cur_'].append(' '*4 + line)
        elif kind == 'init':
            # some extra code for a Node's __init__ method
            name = mo.group(1)
            cur = classes[name]
        elif kind == 'flatten_nodes':
            # special case for getChildNodes flattening
            name = mo.group(1)
            attr = mo.group(2)
            cur = classes[name]
            cur.flatten_nodes[attr] = cur.flatten_nodes['_cur_'] = []
        elif kind == 'additional_method':
            name = mo.group(1)
            methname = mo.group(2)
            params = mo.group(3)
            cur = classes[name]
            cur.additional_methods['_cur_'] = ['    def %s(%s):\n' % (methname, params)]
            cur.additional_methods[methname] = cur.additional_methods['_cur_']
            
    for node in classes.values():
        node.setup_parent(classes)
    return sorted(classes.values(), key=lambda n: n.name)

ASTVISITORCLASS='''
class ASTVisitor(object):
    """This is a visitor base class used to provide the visit
    method in replacement of the former visitor.visit = walker.dispatch
    It could also use to identify base type for visit arguments of AST nodes
    """

    def default(self, node):
        for child in node.getChildNodes():
            child.accept(self)

'''

def gen_ast_visitor(classes):
    print ASTVISITORCLASS
    buf = StringIO()
    for info in classes:
        info.gen_base_visit(buf)
    print buf.getvalue()

def main():
    prologue, epilogue = load_boilerplate(sys.argv[-1])
    print prologue
    print
    classes = parse_spec(SPEC)
    for info in classes:
        print info.gen_source()
    gen_ast_visitor(classes)
    print epilogue

if __name__ == "__main__":
    main()
    sys.exit(0)

### PROLOGUE
"""Python abstract syntax node definitions

This file is automatically generated by Tools/compiler/astgen.py
"""
from consts import CO_VARARGS, CO_VARKEYWORDS, OP_ASSIGN
from pypy.interpreter.baseobjspace import Wrappable

def flatten(list):
    l = []
    for elt in list:
        t = type(elt)
        if t is tuple or t is list:
            for elt2 in flatten(elt):
                l.append(elt2)
        else:
            l.append(elt)
    return l

#def flatten_nodes(list):
#    return [n for n in flatten(list) if isinstance(n, Node)]

nodes = {}

class Node(Wrappable):
    """Abstract base class for ast nodes."""
    def __init__(self, lineno = -1):
        self.lineno = lineno
        self.filename = ""
        
    def getChildren(self):
        pass # implemented by subclasses
    def __iter__(self):
        for n in self.getChildren():
            yield n
    def asList(self): # for backwards compatibility
        return self.getChildren()
    def getChildNodes(self):
        return [] # implemented by subclasses
    def accept(self, visitor):
        raise NotImplentedError
    def flatten(self):
        res = []
        nodes = self.getChildNodes()
        if nodes:
            for n in nodes:
                res.extend( n.flatten() )
        else:
            res.append( self )
        return res

        
class EmptyNode(Node):
    def accept(self, visitor):
        return visitor.visitEmptyNode(self)

class Expression(Node):
    # Expression is an artificial node class to support "eval"
    nodes["expression"] = "Expression"
    def __init__(self, node):
        Node.__init__(self)
        self.node = node

    def getChildren(self):
        return [self.node,]

    def getChildNodes(self):
        return [self.node,]

    def __repr__(self):
        return "Expression(%s)" % (repr(self.node))

    def accept(self, visitor):
        return visitor.visitExpression(self)

### EPILOGUE
for name, obj in globals().items():
    if isinstance(obj, type) and issubclass(obj, Node):
        nodes[name.lower()] = obj
