from pypy.jit.codegen.ppc.ppcgen.field import Field
from pypy.jit.codegen.ppc.ppcgen import regname

fields = { # bit margins are *inclusive*! (and bit 0 is
           # most-significant, 31 least significant)
    "opcode": ( 0,  5),
    "AA":     (30, 30),
    "BD":     (16, 29, 'signed'),
    "BI":     (11, 15),
    "BO":     ( 6, 10),
    "crbA":   (11, 15),
    "crbB":   (16, 20),
    "crbD":   ( 6, 10),
    "crfD":   ( 6,  8),
    "crfS":   (11, 13),
    "CRM":    (12, 19),
    "d":      (16, 31, 'signed'),
    "FM":     ( 7, 14),
    "frA":    (11, 15, 'unsigned', regname._F),
    "frB":    (16, 20, 'unsigned', regname._F),
    "frC":    (21, 25, 'unsigned', regname._F),
    "frD":    ( 6, 10, 'unsigned', regname._F),
    "frS":    ( 6, 10, 'unsigned', regname._F),
    "IMM":    (16, 19),
    "L":      (10, 10),
    "LI":     ( 6, 29, 'signed'),
    "LK":     (31, 31),
    "MB":     (21, 25),
    "ME":     (26, 30),
    "NB":     (16, 20),
    "OE":     (21, 21),
    "rA":     (11, 15, 'unsigned', regname._R),
    "rB":     (16, 20, 'unsigned', regname._R),
    "Rc":     (31, 31),
    "rD":     ( 6, 10, 'unsigned', regname._R),
    "rS":     ( 6, 10, 'unsigned', regname._R),
    "SH":     (16, 20),
    "SIMM":   (16, 31, 'signed'),
    "SR":     (12, 15),
    "spr":    (11, 20),
    "TO":     ( 6, 10),
    "UIMM":   (16, 31),
    "XO1":    (21, 30),
    "XO2":    (22, 30),
    "XO3":    (26, 30),
}


class IField(Field):
    def __init__(self, name, left, right, signedness):
        assert signedness == 'signed'
        super(IField, self).__init__(name, left, right, signedness)
    def encode(self, value):
        # XXX should check range
        value &= self.mask << 2 | 0x3
        return value & ~0x3
    def decode(self, inst):
        mask = self.mask << 2
        v = inst & mask
        if self.signed and (~mask >> 1) & mask & v:
            return ~(~v&self.mask)
        else:
            return v
    def r(self, i, labels, pc):
        if not ppc_fields['AA'].decode(i):
            v = self.decode(i)
            if pc+v in labels:
                return "%s (%r)"%(v, ', '.join(labels[pc+v]))
        else:
            return self.decode(i)


class spr(Field):
    def encode(self, value):
        value = (value&31) << 5 | (value >> 5 & 31)
        return super(spr, self).encode(value)
    def decode(self, inst):
        value = super(spr, self).decode(inst)
        return (value&31) << 5 | (value >> 5 & 31)

# other special fields?

ppc_fields = {
    "LI":  IField("LI", *fields["LI"]),
    "BD":  IField("BD", *fields["BD"]),
    "spr": spr("spr",   *fields["spr"]),
}

for f in fields:
    if f not in ppc_fields:
        ppc_fields[f] = Field(f, *fields[f])
