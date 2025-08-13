# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass
from mutagen._file import FileType # pyright: ignore

from .types import SeratoTags, EntryBase
from .utils import get_serato_metadata

@dataclass
class Analysis(EntryBase):
    version : list[int]

def get_serato_analysis(audio: FileType) -> Analysis | None:
    out = get_serato_metadata(SeratoTags.ANALYSIS, parse)(audio)
    if out is None:
        return None
    else:
        assert len(out) == 1 and isinstance(out[0], Analysis)
        return out[0]

def parse(b: bytes) -> list[EntryBase]:
    v = []
    for n in range(0, len(b)):
        v = v + [b[n]]
    return [Analysis(v)]
