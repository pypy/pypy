from pypy.objspace.std.register_all import register_all

def wraptuple(space, list_w):
    from pypy.objspace.std.tupleobject import W_TupleObject

    # XXX fix specialisedtuple
    #if space.config.objspace.std.withspecialisedtuple:
    #    from specialisedtupleobject import makespecialisedtuple, NotSpecialised
    #    try:
    #        return makespecialisedtuple(space, list_w)
    #    except NotSpecialised:
    #        pass

    if space.config.objspace.std.withsmalltuple:
        from pypy.objspace.std.smalltupleobject import W_SmallTupleObject2
        from pypy.objspace.std.smalltupleobject import W_SmallTupleObject3
        from pypy.objspace.std.smalltupleobject import W_SmallTupleObject4
        from pypy.objspace.std.smalltupleobject import W_SmallTupleObject5
        from pypy.objspace.std.smalltupleobject import W_SmallTupleObject6
        from pypy.objspace.std.smalltupleobject import W_SmallTupleObject7
        from pypy.objspace.std.smalltupleobject import W_SmallTupleObject8
        if len(list_w) == 2:
            return W_SmallTupleObject2(list_w)
        if len(list_w) == 3:
            return W_SmallTupleObject3(list_w)
        if len(list_w) == 4:
            return W_SmallTupleObject4(list_w)
        if len(list_w) == 5:
            return W_SmallTupleObject5(list_w)
        if len(list_w) == 6:
            return W_SmallTupleObject6(list_w)
        if len(list_w) == 7:
            return W_SmallTupleObject7(list_w)
        if len(list_w) == 8:
            return W_SmallTupleObject8(list_w)
    return W_TupleObject(list_w)

