"""
A script to help generate the slot definitions
"""
from collections import defaultdict
from pypy.module.cpyext.slotdefs import slotdefs
from pypy.module._hpy_universal.llapi import cts

prefixes = ['async', 'number', 'mapping', 'sequence', 'buffer']
SlotEnum = cts.gettype('HPySlot_Slot')

def cname2slot(name):
    for prefix in prefixes:
        if name.startswith('tp_as_%s' % prefix):
            name = name[len('tp_as_%s.c_' % prefix):]
    return 'HPy_' + name

cpy_slot_data = defaultdict(list)
for ts in slotdefs:
    hpyslot = cname2slot(ts.slot_name)
    if not hasattr(SlotEnum, hpyslot):
        continue
    cpy_slot_data[hpyslot].append((ts.method_name, ts.wrapper_class.__name__ if ts.wrapper_class else None))

ALL_SLOTS = sorted(
    [(key, value) for key, value in SlotEnum.__dict__.items() if key.startswith('HPy_')],
    key=lambda x: x[1])
SLOT_DATA = []
for key, value in ALL_SLOTS:
    methods, wrappers = zip(*cpy_slot_data[key]) if cpy_slot_data[key] else ([], [])
    SLOT_DATA.append((value, key, methods, wrappers))

print 'UNARYFUNC_SLOTS = ['
for value, key, methods, wrappers in SLOT_DATA:
    if wrappers == ('wrap_unaryfunc',):
        print "    ('%s', '%s')," % (key[4:], methods[0])
print ']'
print
print 'BINARYFUNC_SLOTS = ['
for value, key, methods, wrappers in SLOT_DATA:
    if wrappers == ('wrap_binaryfunc',):
        print "    ('%s', '%s')," % (key[4:], methods[0])
print ']'
print
