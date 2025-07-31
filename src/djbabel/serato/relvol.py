# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass
from mutagen._file import FileType

from .types import EntryBase, SeratoTags
from .utils import get_serato_metadata, identity

@dataclass
class RelVol(EntryBase):
    value: bytes


def get_serato_relvol(audio: FileType) -> RelVol | None:
    out = get_serato_metadata(SeratoTags.RELVOL, parser)(audio)
    if out is None:
        return None
    else:
        assert len(out) == 1 and isinstance(out[0], RelVol)
        return out[0]


# XXX no parser yet
def parser(data: bytes) -> list[EntryBase]:
    return [RelVol(data)]
