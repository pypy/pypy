import py
from pypy.annotation.model import *
from pypy.rpython.lltypes import *
from pypy.tool.template import compile_template


def substitute_newlist(typer, op):
    s_result = typer.annotator.binding(op.result)
    LIST = getlisttype(typer, s_result)
    T = getlistitemtype(typer, s_result)
    n = len(op.args)
    inputsignature = (T,) * n
    try:
        newlist = typer.newlistcache[LIST, n]
    except KeyError:
        # Make an implementation of newlist(x1,..,xn) which allocates
        # a list with n elements and initialize them.
        List_typ = LIST.TO

        def template():
            args = ', '.join(['arg%d' % i for i in range(n)])
            yield     'def newlist(%s):' % args
            yield     '    l = malloc(List_typ)'
            yield     '    l.items = malloc(List_typ.items.TO, %d)' % n
            for i in range(n):
                yield '    l.items[%d].item = arg%d' % (i, i)
            yield     '    return l'

        newlist = compile_template(template(), 'newlist')
        typer.newlistcache[LIST, n] = newlist
    return typer.substitute_op(op, (newlist,) + inputsignature +  (LIST,))

def getlisttype(typer, s_list):
    assert isinstance(s_list, SomeList)
    listdef = s_list.listdef
    try:
        return typer.listtypecache[listdef]
    except KeyError:
        List_typ = ForwardReference()
        result = typer.listtypecache[listdef] = GcPtr(List_typ)
        define_list(typer, s_list, List_typ)
        return result

def getlistitemtype(typer, s_list):
    return typer.annotation2concretetype(s_list.listdef.listitem.s_value)


def define_list(typer, s_list, List_typ):
    T = getlistitemtype(typer, s_list)
    List_typ.become(Struct("list",
                           ("items", GcPtr(Array(('item',T))))))

    def getitem(l, i):
        return l.items[i].item

    typer['getitem', s_list, SomeInteger()] = (
        getitem, GcPtr(List_typ), Signed, T)

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
