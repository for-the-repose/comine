#__ LGPL 3.0, 2017 Alexander Soloviev (no.friday@yandex.ru)

from re     import compile as ReC
from math   import ceil, log

class Mask(object):
    '''
        Blob search mask parser, has the following forms:
            * Arbitrary hex endoced blob:   :HH..HH
            * Single quoted ASCII string:   'string'
            * Integer with endianness:      value[_[bits][lbn]]
    '''

    __HEX = ReC(':([0-9a-fA-F]+)')
    __NUM = ReC('([0-9xa-fA-F]+)(?:_([0-9p]+)?([lbn])?)?')

    def __init__(s, bits, le):
        s.__bits    = bits      # Native pointer length
        s.__little  = le        # Native integer endianness

    def __call__(s, line):
        if line.startswith(':'):
            m = s.__HEX.match(line)

            if m is not None and len(m.group(1)) % 2 == 0:
                return m.group(1).decode('hex')

        elif len(line) > 1 and (line[0] == line[-1] == "'"):
            return line[1:-1]

        else:
            m = s.__NUM.match(line)

            if m is not None:
                vol, bits, end = m.groups()

                bits = s.__bits if bits == 'p' else int(bits or 0)
                le = s.__little if end in (None, 'n') else end == 'l'

                if bits == 0 and vol.startswith('0x'):
                    bits = s.__calc_bits((len(vol) - 2) * 4)

                if bits % 8 == 0:
                    try:
                        vol = int(vol, 0)
                    except TypeError:
                        pass
                    else:
                        bits = bits or s.__calc_bits(int(1 + log(vol or 1, 2)))

                        return s.__value_to(vol, bits, le)

    def __calc_bits(s, bits):
        return 2 ** max(3, int(ceil(log(max(1, bits), 2))))

    def __value_to(s, val, bits, le):
        chars = map(lambda x: (val >> x) & 0xff, xrange(0, bits, 8))

        return str(bytearray(chars if le else reversed(chars)))
