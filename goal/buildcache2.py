
def buildcache(space):
    from pypy.interpreter.typedef import interptypes
    
    space.builtin.getdict()
    print "*builtin*"
    w_dic = space.builtin.w_dict
    #print space.unwrap(space.call_method(w_dic,"keys"))
    

    space.sys.getdict()
    print "*sys*"
    w_dic = space.sys.w_dict
    #print space.unwrap(space.call_method(w_dic,"keys"))
    space.delitem(w_dic,space.wrap("pypy_getudir"))
    print " * removed pypy_getudir"

    for typedef in interptypes:
        w_typ = space.gettypeobject(typedef)
        w_typ.getdict()
        print "*%s*" % typedef.name
        
    for typedef in space.model.pythontypes:
        w_typ = getattr(space, 'w_' + typedef.name)
        w_typ.getdict()

        print "*%s*" % typedef.name
        #print w_typ.dict_w.keys()

    space.builtin.get('file').getdict()

    space.appexec([],"""():
    try:
       raise ValueError
    except ValueError:
       pass
    exec 'pass'    
""")
    # freeze caches?
    print "cache build finished"

if __name__ == '__main__':
    import autopath    
    from pypy.objspace.std.objspace import StdObjSpace

    space = StdObjSpace()

    buildcache(space)
