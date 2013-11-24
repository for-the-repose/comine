#__ LGPL 3.0, 2013 Alexander Soloviev (no.friday@yandex.ru)

from struct     import Struct

def hexdump(s, bpl = 16, ident = 0):
    out = []

    total = (len(s) + bpl - 1) / bpl

    for x in xrange(total):
        out.append(' ' * ident)
        out.append('%3.3x' % (x * bpl,))

        line = s[x*bpl: (x+1)*bpl]

        for y in xrange(len(line)):
            out.append(' %02.2x' % ord(line[y]))

        out.append('   ' * (bpl - y))
        out.append('  ')

        for y in xrange(len(line)):
            if 0x1f < ord(line[y]) < 0x80:
                out.append(line[y])
            else:
                out.append('.')

        out.append('\n')

    return ''.join(out)


def read_tlv(blob):
    offset, total = 0, len(blob)

    pat = Struct(">HH")

    while offset + pat.size <= total:
        tag, size = pat.unpack_from(blob, offset)

        offset += pat.size + size

        if offset > total:
            yield None

        else:
            yield(tag, blob[offset-size:offset])

    if offset != total:
        yield None


def read_str_08_arr(blob):
    offset, total = 0, len(blob)

    pat = Struct(">B")

    while offset < total:
        size, = pat.unpack_from(blob, offset)

        offset += pat.size

        yield (blob[offset:offset + size])

        offset += size

