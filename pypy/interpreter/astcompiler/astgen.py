"""Generate ast module from specification

This script generates the ast module from a simple specification,
which makes it easy to accomodate changes in the grammar.  This
approach would be quite reasonable if the grammar changed often.
Instead, it is rather complex to generate the appropriate code.  And
the Node interface has changed more often than the grammar.
"""
# This is a heavily modified version from the original that adds a
# visit method to each node

import fileinput
import getopt
import re
import sys
from StringIO import StringIO

SPEC = "ast.txt"
COMMA = ", "

def strip_default(arg):
    """Return the argname from an 'arg = default' string"""
    i = arg.find('=')
    if i == -1:
        return arg
    t = arg[:i].strip()
    return t

P_NODE = 1
P_OTHER = 2
P_STR = 3
P_INT = 4
P_STR_LIST = 5
P_INT_LIST = 6
P_WRAPPED = 7
P_NESTED = 8
P_NONE = 9

class NodeInfo:
    """Each instance describes a specific AST node"""
    def __init__(self, name, args, parent=None):
        self.name = name
        self.args = args.strip()
        self.argnames = self.get_argnames()
        self.argprops = self.get_argprops()
        self.nargs = len(self.argnames)
        self.init = []
        self.applevel_new = []
        self.applevel_mutate = []
        self.flatten_nodes = {}
        self.mutate_nodes = {}
        self.additional_methods = {}
        self.parent = parent

    def setup_parent(self, classes):
        if self.parent:
            self.parent = classes[self.parent]
        else:
            self.parent = Node_NodeInfo

    def get_argnames(self):
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
            elif arg.endswith('*int'):
                arg = self.argnames[i] = arg[:-4]
                d[arg] = P_INT
                hardest_arg = max(hardest_arg, P_INT)
            elif arg.endswith('*str'):
                arg = self.argnames[i] = arg[:-4]
                d[arg] = P_STR
                hardest_arg = max(hardest_arg, P_STR)
            elif arg.endswith('*[int]'):
                arg = self.argnames[i] = arg[:-6]
                d[arg] = P_INT_LIST
                hardest_arg = max(hardest_arg, P_INT_LIST)
            elif arg.endswith('*[str]'):
                arg = self.argnames[i] = arg[:-6]
                d[arg] = P_STR_LIST
                hardest_arg = max(hardest_arg, P_STR_LIST)
            elif arg.endswith('%'):
                arg = self.argnames[i] = arg[:-1]
                d[arg] = P_WRAPPED
                hardest_arg = max(hardest_arg, P_WRAPPED)
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
            self.args = self.args.replace('*str', '')
            self.args = self.args.replace('*int', '')
            self.args = self.args.replace('*[str]', '')
            self.args = self.args.replace('*[int]', '')
            self.args = self.args.replace('*', '')
            self.args = self.args.replace('!', '')
            self.args = self.args.replace('&', '')
            self.args = self.args.replace('%', '')

        return d

    def get_initargs(self):
        if self.parent.args and self.args:
            args = self.parent.args +","+ self.args
        else:
            args = self.parent.args or self.args
        return args

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
        print >> buf
        self._gen_mutate(buf)
        print >> buf
        self._gen_attrs(buf)
        print >> buf
        self._gen_new(buf)
        print >> buf
        self._gen_typedef(buf)
        buf.seek(0, 0)
        return buf.read()

    def _gen_init(self, buf):
        initargs = self.get_initargs()
        if initargs:
            print >> buf, "    def __init__(self, %s, lineno=-1):" % initargs
        else:
            print >> buf, "    def __init__(self, lineno=-1):"
        if self.parent.args:
            print >> buf, "        %s.__init__(self, %s, lineno)" % (self.parent.name, self.parent.args)
        else:
            print >> buf, "        Node.__init__(self, lineno)"
        if self.argnames:
            for name in self.argnames:
                if name in self.flatten_nodes:
                    print >>buf, "    %s" % self.flatten_nodes[name][0].rstrip()
                print >> buf, "        self.%s = %s" % (name, name)
        if self.init:
            print >> buf, "".join(["    " + line for line in self.init])

    def _gen_new(self, buf):
        if self.applevel_new:
            print >> buf, ''.join(self.applevel_new)
            return
        args = self.get_initargs()
        argprops = self.argprops
        if args:
            w_args = ['w_%s' % strip_default(arg.strip())
                      for arg in args.split(',') if arg]
            print >> buf, "def descr_%s_new(space, w_subtype, %s, lineno=-1):" % (self.name, ', '.join(w_args))
        else:
            w_args = []
            print >> buf, "def descr_%s_new(space, w_subtype, lineno=-1):" % (self.name,)
        print >> buf, "    self = space.allocate_instance(%s, w_subtype)" % (self.name,)
        # w_args = ['w_%s' % strip_default(arg.strip()) for arg in self.args.split(',') if arg]
        for w_arg in w_args:
            argname = w_arg[2:]
            prop = argprops[argname]
            if prop == P_NONE:
                print >> buf, "    %s = space.interp_w(Node, %s, can_be_None=True)" % (argname, w_arg)
            elif prop == P_NODE:
                print >> buf, "    %s = space.interp_w(Node, %s, can_be_None=False)" % (argname, w_arg)
            elif prop == P_NESTED:
                print >> buf, "    %s = [space.interp_w(Node, w_node) for w_node in space.unpackiterable(%s)]" % (argname, w_arg)
            elif prop == P_STR:
                print >> buf, "    %s = space.str_w(%s)" % (argname, w_arg)
            elif prop == P_INT:
                print >> buf, "    %s = space.int_w(%s)" % (argname, w_arg)
            elif prop == P_STR_LIST:
                print >> buf, "    %s = [space.str_w(w_str) for w_str in space.unpackiterable(%s)]" % (argname, w_arg)
            elif prop == P_INT_LIST:
                print >> buf, "    %s = [space.int_w(w_int) for w_int in space.unpackiterable(%s)]" % (argname, w_arg)
            elif prop == P_WRAPPED:
                print >> buf, "    # This dummy assingment is auto-generated, astgen.py should be fixed to avoid that"
                print >> buf, "    %s = %s" % (argname, w_arg)
            else:
                raise ValueError("Don't know how to handle property '%s'" % prop)
            print >> buf, "    self.%s = %s" % (argname, argname)
        print >> buf, "    self.lineno = lineno"
        print >> buf, "    return space.wrap(self)"

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
                    name = self.argnames[0]
                    if self.argprops[name] == P_NESTED:
                        print >> buf, "        return tuple(flatten(self.%s))" % name
                    else:
                        print >> buf, "        return (self.%s,)" % name
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
            vals = ["self.%s.__repr__()" % name for name in self.argnames]
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


    def _gen_insertnodes_func(self, buf):
        print >> buf, "    def descr_insert_after(space, self, node, w_added_nodes):"
        print >> buf, "        added_nodes = [space.interp_w(Node, w_node) for w_node in space.unpackiterable(w_added_nodes)]"
        print >> buf, "        index = self.nodes.index(node) + 1"
        print >> buf, "        self.nodes[index:index] = added_nodes"
        print >> buf
        print >> buf, "    def descr_insert_before(space, self, node, w_added_nodes):"
        print >> buf, "        added_nodes = [space.interp_w(Node, w_node) for w_node in space.unpackiterable(w_added_nodes)]"
        print >> buf, "        index = self.nodes.index(node)"
        print >> buf, "        self.nodes[index:index] = added_nodes"


    def _gen_mutate(self, buf):
        print >> buf, "    def mutate(self, visitor):"
        if len(self.argnames) != 0:
            for argname in self.argnames:
                if argname in self.mutate_nodes:
                    for line in self.mutate_nodes[argname]:
                        if line.strip():
                            print >> buf, '    ' + line
                elif self.argprops[argname] == P_NODE:
                    print >> buf, "        self.%s = self.%s.mutate(visitor)" % (argname,argname)
                elif self.argprops[argname] == P_NONE:
                    print >> buf, "        if self.%s is not None:" % (argname,)
                    print >> buf, "            self.%s = self.%s.mutate(visitor)" % (argname,argname)
                elif self.argprops[argname] == P_NESTED:
                    print >> buf, "        visitor._mutate_list(self.%s)"%(
                        argname,)
        print >> buf, "        return visitor.visit%s(self)" % self.name

    def _gen_fget_func(self, buf, attr, prop ):
        # FGET
        print >> buf, "    def fget_%s( space, self):" % attr
        if prop[attr]==P_WRAPPED:
            print >> buf, "        return self.%s" % attr
        elif prop[attr] in (P_INT,P_STR, P_NODE):
            print >> buf, "        return space.wrap(self.%s)" % attr
        elif prop[attr] in (P_INT_LIST, P_STR_LIST, P_NESTED ):
            print >> buf, "        return space.newlist( [space.wrap(itm) for itm in self.%s] )" % attr
        elif prop[attr]==P_NONE:
            print >> buf, "        if self.%s is None:" % attr
            print >> buf, "            return space.w_None"
            print >> buf, "        else:"
            print >> buf, "            return space.wrap(self.%s)" % attr
        else:
            assert False, "Unkown node type"

    def _gen_fset_func(self, buf, attr, prop ):
        # FSET
        print >> buf, "    def fset_%s( space, self, w_arg):" % attr
        if prop[attr] == P_WRAPPED:
            print >> buf, "        self.%s = w_arg" % attr
        elif prop[attr] == P_INT:
            print >> buf, "        self.%s = space.int_w(w_arg)" % attr
        elif prop[attr] == P_STR:
            print >> buf, "        self.%s = space.str_w(w_arg)" % attr
        elif prop[attr] == P_INT_LIST:
            print >> buf, "        del self.%s[:]" % attr
            print >> buf, "        for itm in space.unpackiterable(w_arg):"
            print >> buf, "            self.%s.append( space.int_w(itm) )" % attr
        elif prop[attr] == P_STR_LIST:
            print >> buf, "        del self.%s[:]" % attr
            print >> buf, "        for itm in space.unpackiterable(w_arg):"
            print >> buf, "            self.%s.append( space.str_w(itm) )" % attr
        elif prop[attr] == P_NESTED:
            print >> buf, "        del self.%s[:]" % attr
            print >> buf, "        for w_itm in space.unpackiterable(w_arg):"
            print >> buf, "            self.%s.append( space.interp_w(Node, w_itm))" % attr
        elif prop[attr] == P_NONE:
            print >> buf, "        self.%s = space.interp_w(Node, w_arg, can_be_None=True)" % attr
        else: # P_NODE
            print >> buf, "        self.%s = space.interp_w(Node, w_arg, can_be_None=False)" % attr

    def _gen_attrs(self, buf):
        prop = self.argprops
        for attr in self.argnames:
            if "fget_%s" % attr not in self.additional_methods:
                self._gen_fget_func( buf, attr, prop )

            if "fset_%s" % attr not in self.additional_methods:
                self._gen_fset_func( buf, attr, prop )
            if prop[attr] == P_NESTED and attr == 'nodes':
                self._gen_insertnodes_func(buf)

    def _gen_descr_mutate(self, buf):
        if self.applevel_mutate:
            print >> buf, ''.join(self.applevel_mutate)
            return
        print >> buf, "def descr_%s_mutate(space, w_self, w_visitor): " % self.name
        for argname in self.argnames:
            if self.argprops[argname] in [P_NODE, P_NONE]:
                print >> buf, '    w_%s = space.getattr(w_self, space.wrap("%s"))' % (argname,argname)
                if self.argprops[argname] == P_NONE:
                    indent = '    '
                    print >> buf, '    if not space.is_w(w_%s, space.w_None):' % (argname,)
                else:
                    indent = ''
                print >> buf, indent+'    space.setattr(w_%s, space.wrap("parent"), w_self)' % (argname,)
                print >> buf, indent+'    w_new_%s = space.call_method(w_%s, "mutate", w_visitor)'% (argname,
                                                                                                     argname)
                print >> buf, indent+'    space.setattr(w_self, space.wrap("%s"), w_new_%s)' % ( argname,
                                                                                   argname)
                print >> buf, ""
            elif self.argprops[argname] == P_NESTED:
                print >> buf, '    w_list = space.getattr(w_self, space.wrap("%s"))' % (argname,)
                print >> buf, '    list_w = space.unpackiterable(w_list)'
                print >> buf, '    newlist_w = []'
                print >> buf, '    for w_item in list_w:'
                print >> buf, '        space.setattr(w_item, space.wrap("parent"), w_self)'
                print >> buf, '        w_newitem = space.call_method(w_item, "mutate", w_visitor)'
                print >> buf, '        if not space.is_w(w_newitem, space.w_None):'
                print >> buf, '            newlist_w.append(w_newitem)'
                print >> buf, '    w_newlist = space.newlist(newlist_w)'
                print >> buf, '    space.setattr(w_self, space.wrap("%s"), w_newlist)'%(argname)
                
    
        print >> buf, '    return space.call_method(w_visitor, "visit%s", w_self)' % (self.name,)
        

    def _gen_typedef(self, buf):
        initargs = [strip_default(arg.strip())
                    for arg in self.get_initargs().split(',') if arg]
        if initargs:
            new_unwrap_spec = ['ObjSpace', 'W_Root'] + ['W_Root'] * len(initargs) + ['int']
        else:
            new_unwrap_spec = ['ObjSpace', 'W_Root', 'int']
        parent_type = "%s.typedef" % self.parent.name
        print >> buf, "def descr_%s_accept( space, w_self, w_visitor):" %self.name
        print >> buf, "    return space.call_method(w_visitor, 'visit%s', w_self)" % self.name

        print >> buf, ""
        # mutate stuff
        self._gen_descr_mutate(buf)
        
        print >> buf, ""
        print >> buf, "%s.typedef = TypeDef('%s', %s, " % (self.name, self.name, parent_type)
        print >> buf, "                     __new__ = interp2app(descr_%s_new, unwrap_spec=[%s])," % (self.name, ', '.join(new_unwrap_spec))
        print >> buf, "                     accept=interp2app(descr_%s_accept, unwrap_spec=[ObjSpace, W_Root, W_Root] )," % self.name
        print >> buf, "                     mutate=interp2app(descr_%s_mutate, unwrap_spec=[ObjSpace, W_Root, W_Root] )," % self.name
        for attr in self.argnames:
            print >> buf, "                    %s=GetSetProperty(%s.fget_%s, %s.fset_%s )," % (attr,self.name,attr,self.name,attr)
            if self.argprops[attr] == P_NESTED and attr == "nodes":
                print >> buf, "                     insert_after=interp2app(%s.descr_insert_after.im_func, unwrap_spec=[ObjSpace, %s, Node, W_Root])," % (self.name, self.name)
                print >> buf, "                     insert_before=interp2app(%s.descr_insert_before.im_func, unwrap_spec=[ObjSpace, %s, Node, W_Root])," % (self.name, self.name)
        print >> buf, "                    )"
        print >> buf, "%s.typedef.acceptable_as_base_class = False" % self.name


    def _gen_additional_methods(self, buf):
        for key, value in self.additional_methods.iteritems():
            print >> buf, ''.join(value)
            
    def gen_base_visit(self, buf):
        print >> buf, "    def visit%s(self, node):" % self.name
        print >> buf, "        return self.default( node )"

    def gen_print_visit(self, buf):
        # This is a print visitor for application level tests
        print >> buf, "    def visit%s(self, node):" % self.name
        print >> buf, "        print '%s('," % self.name
        for attr in self.argnames:
            if self.argprops[attr] == P_NODE:
                    print >> buf, "        node.%s.accept(self)" % attr
                    print >> buf, "        print ',',"
            if self.argprops[attr] == P_NONE:
                    print >> buf, "        if node.%s: node.%s.accept(self)" % (attr,attr)
                    print >> buf, "        print ',',"
            elif self.argprops[attr] == P_NESTED:
                    print >> buf, "        for nd in node.%s:" % attr
                    print >> buf, "            nd.accept(self)"
                    print >> buf, "        print ',',"
            else:
                print >> buf, "        print node.%s,','," % attr
        print >> buf, "        print ')',"
            


Node_NodeInfo = NodeInfo("Node","")

rx_init = re.compile('init\((.*)\):')
rx_flatten_nodes = re.compile('flatten_nodes\((.*)\.(.*)\):')
rx_additional_methods = re.compile('(\\w+)\.(\w+)\((.*?)\):')
rx_descr_news_methods = re.compile('def\s+descr_(\\w+)_new\((.*?)\):')
rx_descr_mutate_methods = re.compile('def\s+descr_(\\w+)_mutate\((.*?)\):')
rx_mutate = re.compile('mutate\((.*)\.(.*)\):')
def parse_spec(file):
    classes = {}
    cur = None
    kind = None
    fiter = fileinput.input(file)
    for line in fiter:
        if line.startswith("== OVERRIDES =="):
            break
        comment = line.strip().startswith('#')
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


    for line in fiter:
        mo = None
        mo = rx_init.match(line)
        if mo:
            kind = 'init'
            # some extra code for a Node's __init__ method
            name = mo.group(1)
            cur = classes[name]
            continue

        mo = rx_flatten_nodes.match(line)
        if mo:
            kind = 'flatten_nodes'
            # special case for getChildNodes flattening
            name = mo.group(1)
            attr = mo.group(2)
            cur = classes[name]
            _cur_ = attr
            cur.flatten_nodes[attr] = []
            flatten_expect_comment = True
            continue

        mo = rx_mutate.match(line)
        if mo:
            kind = 'mutate'
            # special case for getChildNodes flattening
            name = mo.group(1)
            attr = mo.group(2)
            cur = classes[name]
            _cur_ = attr
            cur.mutate_nodes[attr] = []
            continue

        mo = rx_additional_methods.match(line)
        if mo:
            kind = 'additional_method'
            name = mo.group(1)
            methname = mo.group(2)
            params = mo.group(3)
            cur = classes[name]
            _cur_ = methname
            cur.additional_methods[_cur_] = ['    def %s(%s):\n' % (methname, params)]
            continue

        mo = rx_descr_news_methods.match(line)
        if mo:
            kind = 'applevel_new'
            name = mo.group(1)
            cur = classes[name]
            cur.applevel_new = [mo.group(0) + '\n']
            continue

        mo = rx_descr_mutate_methods.match(line)
        if mo:
            kind = 'applevel_mutate'
            name = mo.group(1)
            cur = classes[name]
            cur.applevel_mutate = [mo.group(0) + '\n']
            continue

        if kind == 'init':
            # some code for the __init__ method
            cur.init.append(line)
        elif kind == 'flatten_nodes':
            if flatten_expect_comment:
                assert line.strip().startswith("#")
                flatten_expect_comment=False
            cur.flatten_nodes[_cur_].append(line)
        elif kind == 'mutate':
            cur.mutate_nodes[_cur_].append(line)
        elif kind == 'additional_method':
            cur.additional_methods[_cur_].append(' '*4 + line)
        elif kind == 'applevel_new':
            cur.applevel_new.append(line)
        elif kind == 'applevel_mutate':
            cur.applevel_mutate.append(line)
            
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
        """This method is only suitable for when we use accept(visitor),
        not mutate(visitor).  In the latter case it *must* be overridden
        by the visitor, typically to just return an unmodified "node".
        """
        for child in node.getChildNodes():
            child.accept(self)

    def _mutate_list(self, lst):
        i = 0
        while i < len(lst):
            item = lst[i].mutate(self)
            if item is not None:
                lst[i] = item
                i += 1
            else:
                del lst[i]

    def visitExpression(self, node):
        return self.default(node)

    def visitEmptyNode(self, node):
        return self.default(node)

'''

def gen_ast_visitor(classes):
    print ASTVISITORCLASS
    buf = StringIO()
    for info in classes:
        info.gen_base_visit(buf)
    print buf.getvalue()

def gen_print_visitor(classes, f):
    print >>f,  ASTVISITORCLASS
    buf = StringIO()
    for info in classes:
        info.gen_base_visit(buf)
    print >>f, buf.getvalue()
    print >>f, "class ASTPrintVisitor(ASTVisitor):"
    buf = StringIO()
    for info in classes:
        info.gen_print_visit(buf)
    print >>f, buf.getvalue()


def main():
    print prologue
    print
    classes = parse_spec(SPEC)
    emitted = {Node_NodeInfo: True}
    def emit(info):
        if info in emitted:
            return
        emitted[info] = True
        emit(info.parent)
        print info.gen_source()
    for info in classes:
        emit(info)
    gen_ast_visitor(classes)
    gen_print_visitor(classes,file("ast_test.py","w"))
    print epilogue
    
prologue = '''
"""Python abstract syntax node definitions

This file is automatically generated by astgen.py
"""
from consts import CO_VARARGS, CO_VARKEYWORDS, OP_ASSIGN
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, GetSetProperty, interp_attrproperty
from pypy.interpreter.gateway import interp2app, W_Root, ObjSpace
from pypy.interpreter.error import OperationError

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
        self.parent = None
        #self.scope = None
        
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
        raise NotImplementedError
    def mutate(self, visitor):
        raise NotImplementedError
    def flatten(self):
        res = []
        nodes = self.getChildNodes()
        if nodes:
            for n in nodes:
                res.extend( n.flatten() )
        else:
            res.append( self )
        return res

    def __repr__(self):
        return "Node()"

    def descr_repr( self, space ):
        # most of the __repr__ are not RPython, more work is needed
        return space.wrap( self.__repr__() )
    
    def fget_parent(space, self):
        return space.wrap(self.parent)

    def fset_parent(space, self, w_parent):
        self.parent = space.interp_w(Node, w_parent, can_be_None=False)

    def descr_getChildNodes( self, space ):
        lst = self.getChildNodes()
        return space.newlist( [ space.wrap( it ) for it in lst ] )

    def get_value(self):
        pass

def descr_node_accept( space, w_self, w_visitor ):
    return space.call_method( w_visitor, 'visitNode', w_self )

def descr_node_mutate(space, w_self, w_visitor): 
    return space.call_method(w_visitor, 'visitNode', w_self)

def descr_Node_new(space, w_subtype, lineno=-1):
    node = space.allocate_instance(Node, w_subtype)
    node.lineno = lineno
    return space.wrap(node)

Node.typedef = TypeDef('ASTNode',
                       __new__ = interp2app(descr_Node_new, unwrap_spec=[ObjSpace, W_Root, int]),
                       #__repr__ = interp2app(Node.descr_repr, unwrap_spec=['self', ObjSpace] ),
                       getChildNodes = interp2app(Node.descr_getChildNodes, unwrap_spec=[ 'self', ObjSpace ] ),
                       accept = interp2app(descr_node_accept, unwrap_spec=[ ObjSpace, W_Root, W_Root ] ),
                       mutate = interp2app(descr_node_mutate, unwrap_spec=[ ObjSpace, W_Root, W_Root ] ),
                       lineno = interp_attrproperty('lineno', cls=Node),
                       filename = interp_attrproperty('filename', cls=Node),
                       parent=GetSetProperty(Node.fget_parent, Node.fset_parent),
                       )

Node.typedef.acceptable_as_base_class = False
        
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
    def mutate(self, visitor):
        self.node = self.node.mutate(visitor)
        return visitor.visitExpression(self)

    def fget_node(space, self):
        return space.wrap(self.node)
    def fset_node(space, self, w_arg):
        self.node = space.interp_w(Node, w_arg, can_be_None=False)

def descr_expression_new(space, w_subtype, w_node, lineno=-1):
    self = space.allocate_instance(Expression, w_subtype)
    node = space.interp_w(Node, w_node, can_be_None=False)
    self.node = node
    self.lineno = lineno
    return space.wrap(self)

def descr_expression_accept(space, w_self, w_visitor):
    return space.call_method(w_visitor, 'visitExpression', w_self)

def descr_expression_mutate(space, w_self, w_visitor):
    w_node = space.getattr(w_self, space.wrap("node"))
    space.setattr(w_node, space.wrap('parent'), w_self)
    w_new_node = space.call_method(w_node, "mutate", w_visitor)
    space.setattr(w_self, space.wrap("node"), w_new_node)

    return space.call_method(w_visitor, "visitExpression", w_self)

Expression.typedef = TypeDef('Expression', Node.typedef,
                     __new__ = interp2app(descr_expression_new, unwrap_spec=[ObjSpace, W_Root, W_Root, int]),
                     accept=interp2app(descr_expression_accept, unwrap_spec=[ObjSpace, W_Root, W_Root] ),
                     mutate=interp2app(descr_expression_mutate, unwrap_spec=[ObjSpace, W_Root, W_Root] ),
                     node=GetSetProperty(Expression.fget_node, Expression.fset_node ),
                    )

Expression.typedef.acceptable_as_base_class = False
'''

epilogue = '''
nodeclasses = []
for name, obj in globals().items():
    if isinstance(obj, type) and issubclass(obj, Node):
        nodes[name.lower()] = obj
        nodeclasses.append(name)
'''

if __name__ == "__main__":
    main()
    sys.exit(0)

