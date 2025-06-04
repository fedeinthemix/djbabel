# -*- coding: utf-8 -*-
import collections
import io
import struct
from mutagen._file import FileType

from .types import SeratoTags
from .utils import get_serato_metadata, FMT_VERSION, readbytes

def get_serato_beatgrid(audio: FileType) -> dict | None:
    return get_serato_metadata(SeratoTags.BEATGRID, parse)(audio)

###############################################################################
# Code from https://github.com/Holzhaus/serato-tags with minor modifications.
#
# Copyright 2019 Jan Holthuis
#
# original code licensed under the MIT License

NonTerminalBeatgridMarker = collections.namedtuple(
    'NonTerminalBeatgridMarker', (
        'position',
        'beats_till_next_marker',
    )
)
TerminalBeatgridMarker = collections.namedtuple('TerminalBeatgridMarker', (
    'position',
    'bpm',
))

Footer = collections.namedtuple('Footer', (
    'unknown',
))


def parse(data: bytes):
    fp = io.BytesIO(data)
    version = struct.unpack(FMT_VERSION, fp.read(2))
    assert version == (0x01, 0x00)

    num_markers = struct.unpack('>I', fp.read(4))[0]
    for i in range(num_markers):
        position = struct.unpack('>f', fp.read(4))[0]
        data = fp.read(4)
        if i == num_markers - 1:
            bpm = struct.unpack('>f', data)[0]
            yield TerminalBeatgridMarker(position, bpm)
        else:
            beats_till_next_marker = struct.unpack('>I', data)[0]
            yield NonTerminalBeatgridMarker(position, beats_till_next_marker)

    # TODO: What's the meaning of the footer byte?
    yield Footer(struct.unpack('B', fp.read(1))[0])
    # In M4A files this assertion may fail. Is it due to our padding?
    # print(fp.read()) # there is a spurious byte '\x00'.
    # assert fp.read() == b''
