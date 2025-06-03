#!/usr/bin/env python


class RoundingMode(object):
    _immutable_ = True

    def __init__(self, value, literal):
        self.value = value
        self.literal = literal

    def __int__(self):
        return self.value

    def __repr__(self):
        return self.literal


RNE = RoundingMode(0b000, 'rne')  # Round to nearest, ties to even
RTZ = RoundingMode(0b001, 'rtz')  # Round towards zero
RDN = RoundingMode(0b010, 'rdn')  # Round down (towards -inf)
RUP = RoundingMode(0b011, 'rup')  # Round up (towards +inf)
RMM = RoundingMode(0b100, 'rmm')  # Round to nearest, ties to maximum magnitude
DYN = RoundingMode(0b111, 'dyn')  # Use the rounding mode register


all_rounding_modes = [RNE, RTZ, RDN, RUP, RMM, DYN]
