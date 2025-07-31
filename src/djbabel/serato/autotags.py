# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
# SPDX-FileCopyrightText: 2019 Jan Holthuis
#
# SPDX-License-Identifier: MIT

from dataclasses import dataclass
from mutagen._file import FileType # pyright: ignore
import io
import struct

from .types import EntryBase, SeratoTags
from .utils import get_serato_metadata, FMT_VERSION, readbytes

###############################################################################

@dataclass
class AutoTags(EntryBase):
    bpm : float
    autogain : float
    gaindb : float


def get_serato_autotags(audio: FileType) -> AutoTags | None:
    at = get_serato_metadata(SeratoTags.AUTOTAGS, parse)(audio)
    if at is None or len(at) == 0:
        return None
    elif len(at) == 1 and isinstance(at[0], AutoTags):
        return at[0]
    else:
        raise ValueError(f"Unexpected entries for autotags {at}.")

###############################################################################
# Code below this line adapted from https://github.com/Holzhaus/serato-tags
#
# Copyright 2019 Jan Holthuis
#
# Original code licensed under the MIT License. See LICENSE/MIT.txt

def parse(data: bytes) -> list[EntryBase]:
    fp = io.BytesIO(data)
    version = struct.unpack(FMT_VERSION, fp.read(2))
    assert version == (0x01, 0x01)

    out = []
    for _ in range(3):
        data = b''.join(readbytes(fp))
        out += [float(data.decode('ascii'))]
    return [AutoTags(*out)]


def dump(ag : AutoTags):
    bpm = ag.bpm
    autogain = ag.autogain
    gaindb = ag.gaindb
    data = struct.pack(FMT_VERSION, 0x01, 0x01)
    for value, decimals in ((bpm, 2), (autogain, 3), (gaindb, 3)):
        data += '{:.{}f}'.format(value, decimals).encode('ascii')
        data += b'\x00'
    return data
