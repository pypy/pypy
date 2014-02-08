#! /usr/bin/env python
import colorsys

def hsv2ansi(h, s, v):
    # h: 0..1, s/v: 0..1
    if s < 0.001:
        return int(v * 23) + 232
    r, g, b = map(lambda x: int(x * 5), colorsys.hsv_to_rgb(h, s, v))
    return 16 + (r * 36) + (g * 6) + b

def ramp_idx(i, num):
    h = 0.57 + float(i)/num
    s = float(num - i) / i if i > (num * 0.85) else 1
    v = 1
    return hsv2ansi(h, s, v)

def ansi_ramp(num):
    return [ramp_idx(i, num) for i in range(num)]

ansi_ramp80 = ansi_ramp(80)
