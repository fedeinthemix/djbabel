# In ipython run
# %load_ext autoreload
# %autoreload 2

import functools
import sys
sys.path.append('../src')

from pathlib import Path
import warnings
import os

# from typing import cast

from mutagen.id3 import ID3, PRIV
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
import mutagen
from mutagen._file import FileType
import struct
import base64
from functools import reduce
from dataclasses import dataclass, fields

import djbabel.serato.markers2
import djbabel.serato.beatgrid
from djbabel.serato.markers2 import CueEntry, get_serato_markers_v2, ColorEntry, BpmLockEntry
from djbabel.serato.utils import audio_file_type, readbytes, serato_metadata
from djbabel.serato.types import SeratoTags, EntryBase
from djbabel.serato.autotags import get_serato_autotags
from djbabel.serato.overview import get_serato_overview
from djbabel.serato.beatgrid import get_serato_beatgrid, NonTerminalBeatgridMarker, TerminalBeatgridMarker
from djbabel.serato.markers import get_serato_markers
from djbabel.serato.analysis import get_serato_analysis
from djbabel.serato.relvol import get_serato_relvol

from djbabel.serato.utils import serato_metadata, parse_serato_envelope, serato_tag_marker, serato_tag_name, audio_file_type, maybe_metadata, get_serato_metadata
from djbabel.types import ABeatGridBPM, ADataSource, AFormat, AMarkerType, AMarker, ASoftware, ATrack, ABeatGrid, ABeatGridBPM, ALoudness

from djbabel.serato import from_serato_audio

#####################################################

file_mp3 = Path("audio") / "The_Todd_Terry_Project_-_Weekend.mp3"
file_flac = Path("audio") / "MARRS-Pump_up_the_volume.flac"
file_m4a = Path("audio") / "blow-go.m4a"

audio_mp3: MP3 = mutagen.File(file_mp3, easy=False) # type: ignore[reportUnknownMemberType]
audio_flac = mutagen.File(file_flac, easy=False)
audio_m4a = mutagen.File(file_m4a, easy=False)

mv2_b_mp3 = serato_metadata(audio_mp3, SeratoTags.MARKERS2)
mv2_b_flac = serato_metadata(audio_flac, SeratoTags.MARKERS2)
mv2_b_m4a = serato_metadata(audio_m4a, SeratoTags.MARKERS2)

mv2_mp3: list[EntryBase] = get_serato_markers_v2(audio_mp3)
mv2_flac = get_serato_markers_v2(audio_flac)
mv2_m4a = get_serato_markers_v2(audio_m4a)

ag_b_mp3 = serato_metadata(audio_mp3, SeratoTags.AUTOTAGS)
ag_b_flac = serato_metadata(audio_flac, SeratoTags.AUTOTAGS)
ag_b_m4a = serato_metadata(audio_m4a, SeratoTags.AUTOTAGS)

ag_mp3 = get_serato_autotags(audio_mp3)
ag_flac = get_serato_autotags(audio_flac)
ag_m4a = get_serato_autotags(audio_m4a)

ov_mp3 = get_serato_overview(audio_mp3)
ov_flac = get_serato_overview(audio_flac)
ov_m4a = get_serato_overview(audio_m4a)
img_mp3 = ov_mp3[SeratoTags.OVERVIEW.name.lower()].show()
img_flac = ov_flac[SeratoTags.OVERVIEW.name.lower()].show()
img_m4a = ov_m4a[SeratoTags.OVERVIEW.name.lower()].show()

bg_mp3 = get_serato_beatgrid(audio_mp3)
bg_flac = get_serato_beatgrid(audio_flac)
bg_m4a = get_serato_beatgrid(audio_m4a)

m_b_mp3 = serato_metadata(audio_mp3, SeratoTags.MARKERS)
m_b_flac = serato_metadata(audio_flac, SeratoTags.MARKERS)
m_b_m4a = serato_metadata(audio_m4a, SeratoTags.MARKERS)

m_mp3 = get_serato_markers(audio_mp3)
m_flac = get_serato_markers(audio_flac) # empty! Works?
# m_m4a = get_serato_markers(audio_m4a) # FAILS !!!  XXXXXXXXXX

an_mp3 = get_serato_analysis(audio_mp3)
an_flac = get_serato_analysis(audio_flac)
an_m4a = get_serato_analysis(audio_m4a)

rv_mp3 = get_serato_relvol(audio_mp3)
rv_flac = get_serato_relvol(audio_flac)
rv_m4a = get_serato_relvol(audio_m4a)

#####################################################
# test example from 
# https://github.com/Holzhaus/triseratops/blob/main/

test_bpm_bin = b'YXBwbGljYXRpb24vb2N0ZXQtc3RyZWFtAABTZXJhdG8gTWFya2Vyc18AAgUAAAAO//////////8A/////wAAAAAAAP//////////AP////8AAAAAAAD//////////wD/////AAAAAAAA//////////8A/////wAAAAAAAP//////////AP////8AAAAAAAD//////////wD/////AAAAAAMA//////////8A/////wAAAAADAP//////////AP////8AAAAAAwD//////////wD/////AAAAAAMA//////////8A/////wAAAAADAP//////////AP////8AAAAAAwD//////////wD/////AAAAAAMA//////////8A/////wAAAAADAP//////////AP////8AAAAAAwAA////A'

test_bpm_bin_b_p = parse_serato_envelope(base64.b64decode(test_bpm_bin + b'A=='), b'Serato Markers_')

# 5 Cues (0x00) and 9 Loops (0x03)
print(hexdump(test_bpm_bin_b_p[6:], 19))

file_m4a = Path("audio") / "blow-go.m4a"
m_b_m4a = serato_metadata(audio_m4a, SeratoTags.MARKERS)
print(hexdump(m_b_m4a[6:], 19))

# MP4 format is
#
# header as MP3
# 4 bytes (start time), 4 bytes (end time), 00 ff ff ff ff 00, 3 bytes (RGB color), 1 byte color
# 00 ff ff ff 00 (footer)
#
# start/stop  time == ff ff ff ff -> not set, other data not meaninful
#
#####################################################


def hexdump(data: bytes, length=16, sep=' '):
    """
    Produce a hexadecimal dump of bytes data.

    Args:
        data (bytes): The bytes object to dump.
        length (int): The number of bytes to display per line.
        sep (str): Separator between hex bytes.
    """
    filter_func = lambda c: (chr(c) if 32 <= c < 127 else '.')
    lines = []
    for i in range(0, len(data), length):
        chunk = data[i:i + length]
        hexa = sep.join([f'{b:02x}' for b in chunk])
        text = ''.join([filter_func(b) for b in chunk])
        lines.append(f'{i:08x}: {hexa:<{length * (len(sep) + 2) - len(sep)}} {text}')
    return '\n'.join(lines)

print(hexdump(mv2_b_m4a))
print(hexdump(mv2_b_mp3))

##########################################################
# CRATES

import io

from djbabel.serato.crate import CrateFieldKind, take_field, take_field_type, parse_field_bool, Unknown, take_fields, created_classes, get_track_paths

fn = Path('subcrates') / 'FEBE_MIX_80_90.crate'
with open(fn, "rb") as f:
    data = f.read()

fp = io.BytesIO(data)
fields = take_fields(fp)

get_track_paths(fields)

##########################################################

a2 = from_serato_audio(audio_mp3)

##########################################################

# Local Variables:
# python-shell-interpreter: "ipython"
# python-shell-interpreter-args: "--simple-prompt"
# End:
