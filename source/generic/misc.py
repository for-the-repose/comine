#__ LGPL 3.0, 2013 Alexander Soloviev (no.friday@yandex.ru)

from struct     import Struct

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

