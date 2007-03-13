""" even lighter weight replacement for templess

    see README_TEMPLESSER.txt for more details
"""

import re

class template(object):
    """ string interpolation on steriods """
    def __init__(self, input):
        self.input = input
        
    def unicode(self, context):
        """ resolve interpolations using context as data dict """
        data = self.input
        data = self._resolve_repeats(data, context)
        data = self._resolve_conditionals(data, context)
        data = data % context
        return data

    _reg_cond_1 = re.compile(r'([^%])([%]{2})*[%][(]([^)]+)[)][[]c(.*)'
                             r'[%][(]\3[)][]]c(.*?)$', re.S | re.U)
    _reg_cond_2 = re.compile(r'^[%][(]([^)]+)[)][[]c(.*)'
                             r'[%][(]\1[)][]]c(.*?)$', re.S | re.U)
    def _resolve_conditionals(self, data, context):
        while 1:
            match = self._reg_cond_1.search(data)
            offset = 2
            if not match:
                match = self._reg_cond_2.search(data)
                if not match:
                    break
                offset = 0
            key = match.group(offset + 1)
            pre = data[:data.find(match.group(0))]
            data = pre
            if offset == 2:
                data += (match.group(1) or '') + (match.group(2) or '')
            if context[key]:
                data += match.group(offset + 2) or ''
            data += match.group(offset + 3) or ''
        return data

    _reg_rept_1 = re.compile(r'([^%])([%]{2})*[%][(]([^)]+)[)][[]b(.*)'
                             r'[%][(]\3[)][]]b(.*?)$', re.S | re.U)
    _reg_rept_2 = re.compile(r'^[%][(]([^)]+)[)][[]b(.*)'
                             r'[%][(]\1[)][]]b(.*?)$', re.S | re.U)
    def _resolve_repeats(self, data, context):
        while 1:
            match = self._reg_rept_1.search(data)
            offset = 2
            if not match:
                match = self._reg_rept_2.search(data)
                if not match:
                    break
                offset = 0
            key = match.group(offset + 1)
            # here we just assume the content is an iterable
            processed = []
            for subcontext in context[key]:
                if isinstance(subcontext, dict):
                    t = template(match.group(offset + 2))
                    processed.append(t.unicode(subcontext).replace('%', '%%'))
                else:
                    if not type(subcontext) in [str, unicode]:
                        subcontext = str(subcontext)
                    processed.append(subcontext)
            pre = data[:data.find(match.group(0))]
            data = pre
            if offset == 2:
                data += (match.group(1) or '') + (match.group(2) or '')
            data += ' '.join(processed) + match.group(offset + 3) or ''
        return data

