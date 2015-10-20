
branch_mnemoic_codes = {
    'BRASL':   ('ril',   ['\xC0','\x05']),
    'BCR':     ('rr',    ['\x07']),
    'BC':      ('rx',    ['\x47']),
    'BRC':     ('ri',    ['\xA7','\x04']),
    'BRCL':    ('ril',   ['\xC0','\x04']),
}

arith_mnemic_codes = {
    'AR':      ('rr',    ['\x1A']),
    'AGR':     ('rre',   ['\xB9','\x08']),
    'AGFR':    ('rre',   ['\xB9','\x18']),
    'A':       ('rx',    ['\x5A']),
    'SR':      ('rr',    ['\x1B']),
    'SGR':     ('rre',   ['\xB9','\x09']),
}

all_mnemonic_codes = {
    'AY':      ('rxy',   ['\xE3','\x5A']),
    'AG':      ('rxy',   ['\xE3','\x08']),
    'AGF':     ('rxy',   ['\xE3','\x18']),
    'AHI':     ('ri',    ['\xA7','\x0A']),
    #
    'BXH':     ('rs',    ['\x86']),
    'BXHG':    ('rsy',   ['\xEB','\x44']),
    'BRXH':    ('rsi',   ['\x84']),
    'BRXLG':   ('rie',   ['\xEC','\x45']),
    #
    'NI':      ('si',    ['\x94']),
    'NIY':     ('siy',   ['\xEB','\x54']),
    'NC':      ('ssa',   ['\xD4']),
    'AP':      ('ssb',   ['\xFA']),
    'SRP':     ('ssc',   ['\xF0']),
    'MVCK':    ('ssd',   ['\xD9']),

    'LAY':     ('rxy',   ['\xE3','\x71']),
    'LMD':     ('sse',   ['\xEF']),
    'LMG':     ('rsy',   ['\xEB','\x04']),
    'LGHI':    ('ri',    ['\xA7','\x09']),
    'LR':      ('rr',    ['\x18']),
    'LGR':     ('rre',   ['\xB9','\x04']),

    'PKA':     ('ssf',   ['\xE9']),
    'STMG':    ('rsy',   ['\xEB','\x24']),
}
all_mnemonic_codes.update(arith_mnemic_codes)
all_mnemonic_codes.update(branch_mnemoic_codes)

