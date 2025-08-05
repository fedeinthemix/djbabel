# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
# SPDX-FileCopyrightText: 2019 Jan Holthuis
#
# SPDX-License-Identifier: MIT

from dataclasses import dataclass
import io
import struct
from mutagen._file import FileType # pyright: ignore

from .types import SeratoTags, EntryBase
from .utils import get_serato_metadata, FMT_VERSION

def get_serato_beatgrid(audio: FileType) -> list[EntryBase] | None:
    return get_serato_metadata(SeratoTags.BEATGRID, parse)(audio)

###############################################################################
# Code below this line adapted from https://github.com/Holzhaus/serato-tags
#
# Copyright 2019 Jan Holthuis
#
# Original code licensed under the MIT License. See LICENSE/MIT.txt

@dataclass
class NonTerminalBeatgridMarker(EntryBase):
    position : float
    beats_till_next_marker : int


@dataclass
class TerminalBeatgridMarker(EntryBase):
    position : float
    bpm : float


@dataclass
class Footer(EntryBase):
    unknown : int


def parse(data: bytes) -> list[EntryBase]:
    fp = io.BytesIO(data)
    version = struct.unpack(FMT_VERSION, fp.read(2))
    assert version == (0x01, 0x00)

    num_markers = struct.unpack('>I', fp.read(4))[0]
    out = []
    for i in range(num_markers):
        position = struct.unpack('>f', fp.read(4))[0]
        data = fp.read(4)
        if i == num_markers - 1:
            bpm = struct.unpack('>f', data)[0]
            out += [TerminalBeatgridMarker(position, bpm)]
        else:
            beats_till_next_marker = struct.unpack('>I', data)[0]
            out += [NonTerminalBeatgridMarker(position, beats_till_next_marker)]

    # TODO: What's the meaning of the footer byte?
    out += [Footer(struct.unpack('B', fp.read(1))[0])]
    return out
    # In M4A files this assertion may fail. Is it due to our padding?
    # print(fp.read()) # there is a spurious byte '\x00'.
    # assert fp.read() == b''
