
from pypy.rpython.module.ll_strtod import ll_strtod_parts_to_float
from pypy.rpython.module.support import to_rstr


def test_it():
    data = [
    (("","1","","")     , 1.0),
    (("-","1","","")    , -1.0),
    (("-","1","5","")   , -1.5),
    (("-","1","5","2")  , -1.5e2),
    (("-","1","5","+2") , -1.5e2),
    (("-","1","5","-2") , -1.5e-2),
    ]

    for parts, val in data:
        assert ll_strtod_parts_to_float(*map(to_rstr, parts)) == val
    
