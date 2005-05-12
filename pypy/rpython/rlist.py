import py
from pypy.annotation.model import *
from pypy.rpython.lltypes import *


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
 
        args = ', '.join(['arg%d' % i for i in range(n)])
        lines = []
        lines.append(    'def newlist(%s):' % args)
        lines.append(    '    l = malloc(List_typ)')
        lines.append(    '    l.items = malloc(List_typ.items.TO, %d)' % n)
        for i in range(n):
            lines.append('    l.items[%d].item = arg%d' % (i, i))
        lines.append(    '    return l')
        lines.append(    '')
        miniglobal = {'List_typ': LIST.TO, 'malloc': malloc}
        exec py.code.Source('\n'.join(lines)).compile() in miniglobal
        newlist = typer.newlistcache[LIST, n] = miniglobal['newlist']
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
