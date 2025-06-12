# -*- coding: utf-8 -*-
from mutagen._file import FileType
import io
import struct

from .types import SeratoTags
from .utils import get_serato_metadata, FMT_VERSION, readbytes

def get_serato_autotags(audio: FileType) -> dict[str, float] | None:
    at = get_serato_metadata(SeratoTags.AUTOTAGS, parse, ['bpm', 'autogain', 'gaindb'])(audio)
    return at if isinstance(at, dict) else None

###############################################################################
# Code from https://github.com/Holzhaus/serato-tags with minor modifications.
#
# Copyright 2019 Jan Holthuis
#
# original code licensed under the MIT License

def parse(data: bytes):
    fp = io.BytesIO(data)
    version = struct.unpack(FMT_VERSION, fp.read(2))
    assert version == (0x01, 0x01)

    for _ in range(3):
        data = b''.join(readbytes(fp))
        yield float(data.decode('ascii'))


def dump(bpm, autogain, gaindb):
    data = struct.pack(FMT_VERSION, 0x01, 0x01)
    for value, decimals in ((bpm, 2), (autogain, 3), (gaindb, 3)):
        data += '{:.{}f}'.format(value, decimals).encode('ascii')
        data += b'\x00'
    return data
