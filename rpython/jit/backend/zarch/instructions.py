
branch_mnemonic_codes = {
    'BRASL':   ('ril',   ['\xC0','\x05']),
    'BRAS':    ('ri',    ['\xA7','\x05']),
    'BCR':     ('rr',    ['\x07']),
    'BC':      ('rx',    ['\x47']),
    'BRC':     ('ri',    ['\xA7','\x04']),
    'BRCL':    ('ril',   ['\xC0','\x04']),
}

arith_mnemonic_codes = {
    'AR':      ('rr',    ['\x1A']),
    'AGR':     ('rre',   ['\xB9','\x08']),
    'AGFR':    ('rre',   ['\xB9','\x18']),
    'A':       ('rx',    ['\x5A']),
    'SR':      ('rr',    ['\x1B']),
    'SGR':     ('rre',   ['\xB9','\x09']),

    'AY':      ('rxy',   ['\xE3','\x5A']),
    'AG':      ('rxy',   ['\xE3','\x08']),
    'AGF':     ('rxy',   ['\xE3','\x18']),
    'AHI':     ('ri',    ['\xA7','\x0A']),

    # floating point
}

logic_mnemonic_codes = {
    # AND operations
    'NGR':        ('rre',      ['\xB9','\x80']),
    'NG':         ('rxy',      ['\xE3','\x80']),
    # and one byte and store it back at the op2 position
    'NI':         ('si',       ['\x94']),
    'NIY':        ('siy',      ['\xEB','\x54']),
    'NC':         ('ssa',      ['\xD4']),

    # AND immediate
    'NIHH':       ('ri_u',     ['\xA5', '\x04']),
    'NIHL':       ('ri_u',     ['\xA5', '\x05']),
    'NILH':       ('ri_u',     ['\xA5', '\x06']),
    'NILL':       ('ri_u',     ['\xA5', '\x07']),

    # OR operations
    'OGR':        ('rre',      ['\xB9','\x81']),
    'OG':         ('rxy',      ['\xE3','\x81']),
    # or one byte and store it back at the op2 position
    'OI':         ('si',       ['\x96']),
    'OIY':        ('siy',      ['\xEB','\x56']),

    # OR immediate
    'OIHH':       ('ri_u',     ['\xA5', '\x08']),
    'OIHL':       ('ri_u',     ['\xA5', '\x09']),
    'OILH':       ('ri_u',     ['\xA5', '\x0A']),
    'OILL':       ('ri_u',     ['\xA5', '\x0B']),

    # XOR operations
    'XGR':        ('rre',      ['\xB9','\x82']),
    'XG':         ('rxy',      ['\xE3','\x82']),
    # or one byte and store it back at the op2 position
    'XI':         ('si',       ['\x97']),
    'XIY':        ('siy',      ['\xEB','\x57']),

    # OR immediate
    'OIHH':       ('ri_u',     ['\xA5', '\x08']),
    'OIHL':       ('ri_u',     ['\xA5', '\x09']),
    'OILH':       ('ri_u',     ['\xA5', '\x0A']),
    'OILL':       ('ri_u',     ['\xA5', '\x0B']),
}

memory_mnemonic_codes = {
    # load address
    'LA':      ('rx',    ['\x41']),
    'LAY':     ('rxy',   ['\xE3','\x71']),

    # load memory
    'LMD':     ('sse',   ['\xEF']),
    'LMG':     ('rsy',   ['\xEB','\x04']),
    'LGHI':    ('ri',    ['\xA7','\x09']),
    'LR':      ('rr',    ['\x18']),
    'LGR':     ('rre',   ['\xB9','\x04']),
    'LG':      ('rxy',   ['\xE3','\x04']),

    # store float
    'STE':     ('rx',    ['\x70']),
    'STD':     ('rx',    ['\x60']),

    # load binary float
    # E -> short (32bit),
    # D -> long (64bit),
    # X -> extended (128bit)
    'LER':     ('rr',    ['\x38']),
    'LDR':     ('rr',    ['\x28']),
    'LE':      ('rx',    ['\x78']),
    'LD':      ('rx',    ['\x68']),
    'LEY':     ('rxy',   ['\xED', '\x64']),
    'LDY':     ('rxy',   ['\xED', '\x65']),
    'LZER':    ('rre',   ['\xB3','\x74'], 'r,-'),
    'LZDR':    ('rre',   ['\xB3','\x75'], 'r,-'),

    # load positive, load negative
    'LPEBR':   ('rre',   ['\xB3','\x00']),
    'LPDBR':   ('rre',   ['\xB3','\x10']),

    'LNEBR':   ('rre',   ['\xB3','\x01']),
    'LNDBR':   ('rre',   ['\xB3','\x11']),
}

floatingpoint_mnemonic_codes = {
    'FIEBR':   ('rrf',   ['\xB3','\x57'], 'r,u4,r,-'),
    'FIDBR':   ('rrf',   ['\xB3','\x5F'], 'r,u4,r,-'),

    'CGEBR':   ('rrf',   ['\xB3','\xA8'], 'r,u4,r,-'),
    'CGDBR':   ('rrf',   ['\xB3','\xA9'], 'r,u4,r,-'),

    # arithmetic
    # ADDITION
    'AEBR':    ('rre',   ['\xB3','\x0A']),
    'ADBR':    ('rre',   ['\xB3','\x1A']),
    'AEB':     ('rxe',   ['\xED','\x0A'], 'r,bidl,-'),
    'ADB':     ('rxe',   ['\xED','\x1A'], 'r,bidl,-'),

    # SUBSTRACTION
    'SEBR':    ('rre',   ['\xB3','\x0B']),
    'SDBR':    ('rre',   ['\xB3','\x1B']),
    'SEB':     ('rxe',   ['\xED','\x0B'], 'r,bidl,-'),
    'SDB':     ('rxe',   ['\xED','\x1B'], 'r,bidl,-'),

    # MULTIPLICATION
    'MDBR':    ('rre',   ['\xB3','\x1C']),
    'MDB':     ('rxe',   ['\xED','\x1C'], 'r,bidl,-'),

    # DIVISION
    'DEBR':    ('rre',   ['\xB3','\x0D']),
    'DDBR':    ('rre',   ['\xB3','\x1D']),
    'DEB':     ('rxe',   ['\xED','\x0D'], 'r,bidl,-'),
    'DDB':     ('rxe',   ['\xED','\x1D'], 'r,bidl,-'),
}

all_mnemonic_codes = {
    #
    'BXH':     ('rs',    ['\x86']),
    'BXHG':    ('rsy',   ['\xEB','\x44']),
    'BRXH':    ('rsi',   ['\x84']),
    'BRXLG':   ('rie',   ['\xEC','\x45']),
    #
    'NI':      ('si',    ['\x94']),
    'NIY':     ('siy',   ['\xEB','\x54']),
    'AP':      ('ssb',   ['\xFA']),
    'SRP':     ('ssc',   ['\xF0']),
    'MVCK':    ('ssd',   ['\xD9']),

    'PKA':     ('ssf',   ['\xE9']),
    'STMG':    ('rsy',   ['\xEB','\x24']),

    'SVC':     ('i',     ['\x0A']),
}
all_mnemonic_codes.update(arith_mnemonic_codes)
all_mnemonic_codes.update(logic_mnemonic_codes)
all_mnemonic_codes.update(memory_mnemonic_codes)
all_mnemonic_codes.update(floatingpoint_mnemonic_codes)
all_mnemonic_codes.update(branch_mnemonic_codes)


if __name__ == "__main__":
    print("%d instructions:" % len(all_mnemonic_codes))
    for name, (typeinstr, _) in all_mnemonic_codes.items():
        print(" %s\t(type: %s)" % (name, typeinstr))
