import py
from pypy.annotation.model import *
from pypy.rpython.lltypes import *
from pypy.tool.template import compile_template


class ListType:

    def __init__(self, s_list):
        assert isinstance(s_list, SomeList)
        self.s_list = s_list
        self.s_item = s_list.listdef.listitem.s_value
        self.LIST = ForwardReference()
        self.LISTPTR = GcPtr(self.LIST)
        #self.ITEM = ... see below

    def define(self, typer):
        self.ITEM = typer.annotation2concretetype(self.s_item)
        self.LIST.become(Struct("list",
                                ("items", GcPtr(Array(('item', self.ITEM))))))

        def getitem(l, i):
            return l.items[i].item

        typer['getitem', self.s_list, SomeInteger()] = (
            getitem, self.LISTPTR, Signed, self.ITEM)

    ##    def append(l, newitem):
    ##        length = len(l.items)
    ##        newitems = malloc(List_typ.items.TO, length+1)
    ##        i = 0
    ##        while i<length:
    ##          newitems[i].item = l.items[i].item
    ##          i += 1
    ##        newitems[length].item = newitem
    ##        l.items = newitems

    ##    Registry['getattr', ...



def substitute_newlist(typer, op):
    # Make an implementation of newlist(x1,..,xn) which allocates
    # a list with nbargs elements and initialize them.
    s_result = typer.annotator.binding(op.result)
    listtype = typer.maketype(ListType, s_result)
    LIST = listtype.LIST
    nbargs = len(op.args)

    def template():
        args = ', '.join(['arg%d' % i for i in range(nbargs)])
        yield     'def newlist(%s):' % args
        yield     '    l = malloc(LIST)'
        yield     '    l.items = malloc(LIST.items.TO, %d)' % nbargs
        for i in range(nbargs):
            yield '    l.items[%d].item = arg%d' % (i, i)
        yield     '    return l'

    newlist = compile_template(template(), 'newlist')

    pattern = ('newlist',) + (listtype.s_item,)*nbargs
    substitution = (newlist,) + (listtype.ITEM,)*nbargs + (listtype.LISTPTR,)
    typer[pattern] = substitution
    raise typer.Retry       # the new pattern should match now
