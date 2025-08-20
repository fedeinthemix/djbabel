# SPDX-FileCopyrightText: NONE
#
# SPDX-License-Identifier: CC0-1.0

# In ipython run
# %load_ext autoreload
# %autoreload 2

import functools
import sys

sys.path.append('../src')

from datetime import date
from pathlib import Path, PureWindowsPath, PurePath
import warnings
import os
import string
import io

# from typing import cast

from mutagen.id3 import ID3, PRIV, COMM
import mutagen.id3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
import mutagen
from mutagen._file import FileType
import struct
import base64
from functools import reduce
from dataclasses import dataclass, fields, asdict, Field, replace
from urllib.parse import quote, urljoin, urlsplit
import xml.etree.ElementTree as ET

import djbabel.serato.markers2
import djbabel.serato.beatgrid
from djbabel.serato.markers2 import CueEntry, LoopEntry, get_serato_markers_v2, ColorEntry, BpmLockEntry
from djbabel.serato.utils import audio_file_type, readbytes, serato_metadata, maybe_metadata, FMT_VERSION, readbytes
from djbabel.serato.types import STag, SeratoTags, EntryBase
from djbabel.serato.autotags import get_serato_autotags
from djbabel.serato.overview import get_serato_overview, draw_waveform
from djbabel.serato.beatgrid import get_serato_beatgrid
from djbabel.serato.markers import get_serato_markers
from djbabel.serato.analysis import get_serato_analysis
from djbabel.serato.relvol import get_serato_relvol

from djbabel.serato.utils import serato_metadata, parse_serato_envelope, serato_tag_marker, serato_tag_name, audio_file_type, maybe_metadata, get_serato_metadata
from djbabel.types import ABeatGridBPM, ADataSource, AFormat, AMarkerType, AMarker, APlaylist, ASoftware, ATrack, ABeatGridBPM, ALoudness, ATransformation, AMarkerColors, ASoftwareInfo

from djbabel.serato import from_serato, read_serato_playlist

from djbabel.serato.crate.read import CrateFieldKind, take_field, take_field_type, parse_field_bool, Unknown, take_fields, created_classes, get_track_paths

from djbabel.utils import beatgrid_offset

from djbabel.cli import parse_input_format, parse_output_format

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
img_mp3 = ov_mp3.img.show()
img_flac = ov_flac.img.show()
img_m4a = ov_m4a.img.show()

bg_mp3 = get_serato_beatgrid(audio_mp3)
bg_flac = get_serato_beatgrid(audio_flac)
bg_m4a = get_serato_beatgrid(audio_m4a)

m_b_mp3 = serato_metadata(audio_mp3, SeratoTags.MARKERS)
m_b_flac = serato_metadata(audio_flac, SeratoTags.MARKERS)
m_b_m4a = serato_metadata(audio_m4a, SeratoTags.MARKERS)

m_mp3 = get_serato_markers(audio_mp3)
m_flac = get_serato_markers(audio_flac) # empty! Works?
m_m4a = get_serato_markers(audio_m4a) # FAILS !!!  XXXXXXXXXX

an_mp3 = get_serato_analysis(audio_mp3)
an_flac = get_serato_analysis(audio_flac)
an_m4a = get_serato_analysis(audio_m4a)

rv_mp3 = get_serato_relvol(audio_mp3)
rv_flac = get_serato_relvol(audio_flac)
rv_m4a = get_serato_relvol(audio_m4a)

#####################################################

from djbabel.serato.markers import serato32decode, serato32encode, Entry, dump, dump_m4a, parse, parse_m4a
from djbabel.serato.write import dump_serato_markers_m4a, to_serato_markers

m_b_m4a = serato_metadata(audio_m4a, SeratoTags.MARKERS)
print(hexdump(m_b_m4a[:6], 19)) # header

print(hexdump(m_b_m4a[6:], 19)) # data

print(hexdump(dump_m4a(entry_m4a)[6:], 19)) # data


# start_time_b_m4a = b'\x00\x00\x06\x05'
# start_time_m4a = struct.unpack('>I', start_time_b_m4a)

# entry_b_1_m4a = b'\x00\x00\x06\x05\xff\xff\xff\xff\x00\xff\xff\xff\xff\x00\x88\xcc\x00\x01\x00'

# info_size = struct.calcsize(Entry.FMT_M4A)
# info = struct.unpack(Entry.FMT_M4A, entry_b_1_m4a[:info_size])

# entry_1_m4a = Entry.load_m4a(entry_b_1_m4a)
# entry_1_m4a.dump_m4a()

entry_m4a = parse_m4a(m_b_m4a)
dump_m4a(entry_m4a)

compare_bytes(m_b_m4a, dump_m4a(entry_m4a))



m_b_mp3 = serato_metadata(audio_mp3, SeratoTags.MARKERS)
print(hexdump(m_b_mp3[:6], 22)) # header

print(hexdump(m_b_mp3[6:], 22)) # data
print(hexdump(dump(m_mp3)[6:], 22)) # data

entry_mp3 = parse(m_b_mp3)
# dump_m4a(entry_m4a)

compare_bytes(m_b_mp3, dump(entry_mp3))


# serato32decode(b'\x7f\x7f\x7f\x7f').rjust(4, b'\x00')
# serato32encode(struct.pack('>I', m_mp3[0].start_position)[1:])

at_mp3 = from_serato(mutagen.File(file_mp3, easy=False))
at_flac = from_serato(mutagen.File(file_flac, easy=False))
at_m4a = from_serato(mutagen.File(file_m4a, easy=False))

low_mp3 = to_serato_markers(at_mp3)
low_flac = to_serato_markers(at_flac)
low_m4a = to_serato_markers(at_m4a)

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
# 4 bytes (start time), 4 bytes (end time), 00 ff ff ff ff 00, 3 bytes (RGB color), 1 byte locked
# 00 ff ff ff 00 (footer)
#
# start/stop  time == ff ff ff ff -> not set, other data not meaninful
#
#####################################################
# Serato DJ Pro decoding

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

# from djbabel.traktor.utils import traktor_path
from djbabel.serato.crate.write import write_field, write_fields, field_type, field_name

fn = Path('subcrates') / 'FEBE_MIX_80_90.crate'

# wp = PureWindowsPath('C:\\Users\\beffa\\test.m4a')
# anchor = Path('/run/media/beffa/FBE\\ HDD\\ 1/backups/orione-backpc-windows/')
# relative = Path('Users/beffa')
# pl = read_serato_playlist(fn, trans, anchor, relative)

with open(fn, "rb") as f:
    data = f.read()
  
fp = io.BytesIO(data)

# f1 = take_field(fp)
# f2 = take_field(fp)
# f3 = take_field(fp)

flds = take_fields(fp)
get_track_paths(flds)

## write

data_w = flds[12]
f_type = field_type(data_w)
f_name = field_name(data_w)
length = len(data_w.value)

if f_name == b'vrsn':
    desc = f_name
else:
    desc = f_type + f_name

content = data_w.value

fp_w = io.BytesIO()
# write_field(fp_w, data_w)
bb = write_fields(fp_w, flds)
out_w = fp_w.getvalue()

# compare_bytes(data[:len(out_w)], out_w)
compare_bytes(data, out_w)

## Crate playlist

from djbabel.serato.write import to_serato_playlist, to_serato_markers

caw_ref_mp3 = Path('audio') / 'crate_write_test_ref.mp3'
caw_ref_flac = Path('audio') / 'crate_write_test_ref.flac'
caw_ref_m4a = Path('audio') / 'crate_write_test_ref.m4a'


at_mp3 = from_serato(mutagen.File(caw_ref_mp3, easy=False))
at_flac = from_serato(mutagen.File(caw_ref_flac, easy=False))
at_m4a = from_serato(mutagen.File(caw_ref_m4a, easy=False))

caw_mp3 = Path('audio') / 'crate_write_test.mp3'
caw_flac = Path('audio') / 'crate_write_test.flac'
caw_m4a = Path('audio') / 'crate_write_test.m4a'

at_mp3.location = caw_mp3
at_flac.location = caw_flac
at_m4a.location = caw_m4a

trans = ATransformation(parse_input_format('sdjpro'),
                        parse_output_format('sdjpro'))

crate = Path('subcrates') / 'crate_write_test.crate'

apl = APlaylist('crate_write_test', [at_mp3, at_flac, at_m4a])
to_serato_playlist(apl, crate, trans)

apl_back = read_serato_playlist(crate, trans, anchor=Path(""))

def compare_pl_tracks(ref, pl):
    for (ot, t) in zip(ref.tracks, pl.tracks):
        for f in fields(ot):
            v_ref = getattr(ot, f.name)
            v = getattr(t, f.name)
            if v_ref != v:
                print(f"difference in track {t.title}, field {f.name}")
                print(f"ref {v_ref}, track {v}")

compare_pl_tracks(apl, apl_back)


def compare_track(audio_ref, audio):
    tags_ref = audio_ref.tags
    tags = audio.tags
    differences = False
    if len(tags_ref) != len(tags):
        print("different number of tags!")
        differences = True
    for k in tags.keys():
        v_ref = tags_ref[k]
        v = tags[k]
        if v_ref != v:
            print(f"differt tag {k}, {v_ref} vs. {v}")
            differences = True
    print(f"differences: {differences}")


compare_track(audio_ref, audio_test)
        
############# check Markers writing

from djbabel.serato.markers2 import LoopEntry, CueEntry

audio_fff_mp3 = mutagen.File(caw_mp3, easy=False)
audio_fff_m4a = mutagen.File(caw_m4a, easy=False)
audio_fff_flac = mutagen.File(caw_flac, easy=False)

# should not include serato_markers
audio_fff_flac.tags.keys()

def compare_markers_vs_markers_v2(ms, ms2):
    for m2 in ms2:
        if isinstance(m2, CueEntry):
            if m2.color != ms[m2.index].color:
                print(f"index {m2.index}: color differ {m2.color} vs {ms[m2.index].color}")
            if m2.position != ms[m2.index].start_position:
                print(f"index {m2.index}: start time differ")
        elif isinstance(m2, LoopEntry):
            if m2.color != ms[5 + m2.index].color:
                print(f"index {m2.index}: color differ")
            if m2.locked != ms[5 + m2.index].is_locked:
                print(f"index {m2.index}: is_locked differ")
            if m2.startposition != ms[5 + m2.index].start_position:
                print(f"index {m2.index}: start time differ")
            if m2.endposition != ms[5 + m2.index].end_position:
                print(f"index {m2.index}: start time differ")

m_fff_mp3 = get_serato_markers(audio_fff_mp3)
m2_fff_mp3 = get_serato_markers_v2(audio_fff_mp3)
compare_markers_vs_markers_v2(m_fff_mp3, m2_fff_mp3)

m_fff_m4a = get_serato_markers(audio_fff_m4a)
m2_fff_m4a = get_serato_markers_v2(audio_fff_m4a)
compare_markers_vs_markers_v2(m_fff_m4a, m2_fff_m4a)



#######################


from djbabel.serato.crate.read import created_classes, ReverseOrder


rr = created_classes['ReverseOrder'](False)

match rr:
    case ReverseOrder(v):
        print("1")
    case _:
        print("2")

##########################################################
# REkordbox

from djbabel.rekordbox import to_rekordbox_playlist
from djbabel.rekordbox.write import to_rekordbox

file_mp3_4 = Path('audio') / 'Ultra_Nate_-_Free_(Original_Mix).mp3'
file_mp3_5 = Path('audio') / 'De_Lacy_-_Hideaway_(Deep_Dish_Remix).mp3'

audio_mp3_4 = mutagen.File(file_mp3_4, easy=False)
audio_mp3_5 = mutagen.File(file_mp3_5, easy=False)

a1 = from_serato(audio_mp3)
a_flac = from_serato(audio_flac)
a_m4a = from_serato(audio_m4a)
a4 = from_serato(audio_mp3_4)
a5 = from_serato(audio_mp3_5)

trans = ATransformation(parse_input_format('sdjpro'),
                        parse_output_format('rb7'))

apl = APlaylist("party", [a1, a_flac, a_m4a, a4, a5])
# apl = APlaylist("party", [a1, a_flac, a_m4a])
to_rekordbox_playlist(apl, Path("pl_rekordbox.xml"), trans)

##########################################################
# Write Serato DJ Pro

from djbabel.serato.write import dump_serato_analysis, dump_serato_autotags, dump_serato_beatgrid, format_mp3_std_tag, to_serato_analysis, to_serato_autotags, to_serato_beatgrid, to_serato_markers_v2, dump_serato_markers_v2, add_envelope, insert_newlines, remove_b64padding, to_serato_playlist, to_serato_markers, dump_serato_markers
import djbabel.serato.markers2 as markers2
from djbabel.utils import closest_color_perceptual

def compare_bytes(reference, data):
    if len(reference) != len(data):
        return False
    else:
        for i, e in enumerate(data):
            if e != reference[i]:
                print(f"element {i} differs: ref = {bytes([reference[i]])}, data = {bytes([e])}")
                return False
        return True

def serato_b64decode(data):
    b64data = data.replace(b'\n', b'')
    padding = b'A==' if len(b64data) % 4 == 1 else (b'=' * (-len(b64data) % 4))
    return base64.b64decode(b64data + padding)

# ty = audio_file_type(audio_mp3)
# tag_name = serato_tag_name(SeratoTags.MARKERS2, ty)
# m2_raw = maybe_metadata(audio_mp3, tag_name)

# this already strips 'envelope' from M4A and FLAC
m2_raw = serato_metadata(audio_mp3, SeratoTags.MARKERS2)
m2_low = get_serato_markers_v2(audio_mp3)

a1 = from_serato(audio_mp3)
ce2_mp3 = to_serato_markers_v2(a1)
ce2_bytes = dump_serato_markers_v2(ce2_mp3)
compare_bytes(m2_raw, ce2_bytes)

an_raw = serato_metadata(audio_mp3, SeratoTags.ANALYSIS)
an_bytes = dump_serato_analysis(to_serato_analysis(a1))
compare_bytes(an_raw, an_bytes)

ag_raw = serato_metadata(audio_mp3, SeratoTags.AUTOTAGS)
ag_bytes = dump_serato_autotags(to_serato_autotags(a1))
compare_bytes(ag_raw, ag_bytes)

bg_mp3 = get_serato_beatgrid(audio_mp3)
bg_raw = serato_metadata(audio_mp3, SeratoTags.BEATGRID)
bg_serato = to_serato_beatgrid(a1)
bg_bytes = dump_serato_beatgrid(bg_serato)
# May fail due to the random Footer byte
compare_bytes(bg_raw, bg_bytes)

# Markers
m_mp3 = get_serato_markers(audio_mp3)
m_raw = serato_metadata(audio_mp3, SeratoTags.MARKERS)
m_serato = to_serato_markers(a1)
m_bytes = dump_serato_markers(m_serato, a1.aformat)
compare_bytes(m_raw, m_bytes)


#### FLAC files
at_flac = from_serato(audio_flac)
ty_flac = audio_file_type(audio_flac)

m2_raw_flac = maybe_metadata(audio_flac, serato_tag_name(SeratoTags.MARKERS2, ty_flac))
m2_bytes_flac = dump_serato_markers_v2(to_serato_markers_v2(at_flac))
m2_bytes_flac_env = add_envelope(m2_bytes_flac, SeratoTags.MARKERS2)
compare_bytes(m2_raw_flac, m2_bytes_flac_env)

bg_raw_flac = maybe_metadata(audio_flac, serato_tag_name(SeratoTags.BEATGRID, ty_flac))
bg_orig_flac = get_serato_beatgrid(audio_flac)

bg_flac = to_serato_beatgrid(at_flac)
bg_bytes_flac = dump_serato_beatgrid(bg_flac)
bg_bytes_flac_env = add_envelope(bg_bytes_flac, SeratoTags.BEATGRID)
# The footer bit appears to be random
# May fail due to the random Footer byte
compare_bytes(bg_raw_flac, bg_bytes_flac_env)

# Analysis
an_raw_flac = maybe_metadata(audio_flac, serato_tag_name(SeratoTags.ANALYSIS, ty_flac))
an_raw_payload_flac = serato_metadata(audio_flac, SeratoTags.ANALYSIS)
an_bytes_flac = dump_serato_analysis(to_serato_analysis(at_flac))
an_bytes_flac_env = add_envelope(an_bytes_flac, SeratoTags.ANALYSIS)
compare_bytes(an_raw_payload_flac, an_bytes_flac)
compare_bytes(an_raw_flac, an_bytes_flac_env)

# Autotags
ag_raw_flac = maybe_metadata(audio_flac, serato_tag_name(SeratoTags.AUTOTAGS, ty_flac))
ag_raw_payload_flac = serato_metadata(audio_flac, SeratoTags.AUTOTAGS)
ag_bytes_flac = dump_serato_autotags(to_serato_autotags(at_flac))
ag_bytes_flac_env = add_envelope(ag_bytes_flac, SeratoTags.AUTOTAGS)
compare_bytes(ag_raw_payload_flac, ag_bytes_flac)
compare_bytes(ag_raw_flac, ag_bytes_flac_env)

# empty!
m_raw_flac = maybe_metadata(audio_flac, serato_tag_name(SeratoTags.MARKERS, ty_flac))
m_low_flac = to_serato_markers(at_flac)
if m_low_flac != []:
    m_bytes_flac = dump_serato_markers(m_low_flac, at_flac.aformat)
    m_bytes_flac_env = add_envelope(m_bytes_flac, SeratoTags.MARKERS)
    print(compare_bytes(m_raw_flac, m_bytes_flac_env))
else:
    m_bytes_flac_env = None
    print(m_raw_flac == m_bytes_flac_env)

#### M4A files

# markers2

at_m4a = from_serato(audio_m4a)
ty_m4a = audio_file_type(audio_m4a)

m2_raw_m4a = maybe_metadata(audio_m4a, serato_tag_name(SeratoTags.MARKERS2, ty_m4a))
m2_bytes_m4a = dump_serato_markers_v2(to_serato_markers_v2(at_m4a))
m2_bytes_m4a_env = add_envelope(m2_bytes_m4a, SeratoTags.MARKERS2)
compare_bytes(m2_raw_m4a, m2_bytes_m4a_env)

# Beatgrid

bg_raw_m4a = maybe_metadata(audio_m4a, serato_tag_name(SeratoTags.BEATGRID, ty_m4a))
bg_orig_m4a = get_serato_beatgrid(audio_m4a)

bg_m4a = to_serato_beatgrid(at_m4a)
bg_bytes_m4a = dump_serato_beatgrid(bg_m4a)
bg_bytes_m4a_env = add_envelope(bg_bytes_m4a, SeratoTags.BEATGRID)
# The footer bit appears to be random
# May fail due to the random Footer byte
compare_bytes(bg_raw_m4a, bg_bytes_m4a_env)

# Analysis
an_raw_m4a = maybe_metadata(audio_m4a, serato_tag_name(SeratoTags.ANALYSIS, ty_m4a))
an_raw_payload_m4a = serato_metadata(audio_m4a, SeratoTags.ANALYSIS)
an_bytes_m4a = dump_serato_analysis(to_serato_analysis(at_m4a))
an_bytes_m4a_env = add_envelope(an_bytes_m4a, SeratoTags.ANALYSIS)
compare_bytes(an_raw_payload_m4a, an_bytes_m4a)
compare_bytes(an_raw_m4a, an_bytes_m4a_env)

# Autotags
ag_raw_m4a = maybe_metadata(audio_m4a, serato_tag_name(SeratoTags.AUTOTAGS, ty_m4a))
ag_raw_payload_m4a = serato_metadata(audio_m4a, SeratoTags.AUTOTAGS)
ag_bytes_m4a = dump_serato_autotags(to_serato_autotags(at_m4a))
ag_bytes_m4a_env = add_envelope(ag_bytes_m4a, SeratoTags.AUTOTAGS)
compare_bytes(ag_raw_payload_m4a, ag_bytes_m4a)
compare_bytes(ag_raw_m4a, ag_bytes_m4a_env)

# Markers
m_raw_m4a = maybe_metadata(audio_m4a, serato_tag_name(SeratoTags.MARKERS, ty_m4a))
m_bytes_m4a = dump_serato_markers_m4a(to_serato_markers(at_m4a))
m_bytes_m4a_env = add_envelope(m_bytes_m4a, SeratoTags.MARKERS)
compare_bytes(m_raw_m4a, m_bytes_m4a_env)


prefix = b'application/octet-stream\x00\x00Serato Markers_\x00'
m_b_m4a = serato_b64decode(m_raw_m4a)[len(prefix):]

hexdump(m_b_m4a[6:], 19)

hexdump(m_bytes_m4a[6:], 19)


#####################
#

from djbabel.serato.write import to_serato, add_serato_tag, format_std_tags, format_mp3_std_tag
from djbabel.serato.read import map_to_aformat

trans = ATransformation(ASoftwareInfo(ASoftware.SERATO_DJ_PRO, (3,2,4)),
                        ASoftwareInfo(ASoftware.SERATO_DJ_PRO, (3,2,4)))

# a_test = a1
# a_test_path = Path('audio') / 'test_audio_1.mp3'
# a_test = at_flac
# a_test_path = Path('audio') / 'test_audio_1.flac'
a_test = at_m4a
a_test_path = Path('audio') / 'test_audio_1.m4a'
a_test.location = a_test_path
a_test.title = 'test title'

audio_test = mutagen.File(a_test_path)
audio_test.delete()
audio_test.save()
audio_test = mutagen.File(a_test_path)

to_serato(a_test, trans)
audio_test = mutagen.File(a_test_path)

for tag in audio_test.tags.keys():
    v = audio_test[tag]
    print(f"tag: {tag}, value {v}")

##########################################################
# BeatGrid Shift

from statistics import mean

## Reference: Serato DJ Pro 3.3.2
### beat-marks:
# <TEMPO Inizio="7.403456687927246" Bpm="98.20976257122028" Metro="4/4" Battito="1" />
# <TEMPO Inizio="34.28469467163086" Bpm="98.09374219446505" Metro="4/4" Battito="1" />
# <TEMPO Inizio="46.51789093017578" Bpm="98.53031180993845" Metro="4/4" Battito="1" />
# <TEMPO Inizio="51.389488220214844" Bpm="98.25032052800319" Metro="4/4" Battito="1" />
# <TEMPO Inizio="80.7023696899414" Bpm="97.19731741870298" Metro="4/4" Battito="1" />
# <TEMPO Inizio="85.64077758789062" Bpm="98.18385900845938" Metro="4/4" Battito="1" />
# <TEMPO Inizio="124.7510757446289" Bpm="99.21178785890902" Metro="4/4" Battito="1" />
# <TEMPO Inizio="127.1701431274414" Bpm="97.95985478515789" Metro="4/4" Battito="1" />
# <TEMPO Inizio="139.42005920410156" Bpm="98.25037167212896" Metro="4/4" Battito="1" />
# <TEMPO Inizio="154.0764923095703" Bpm="99.38418182622377" Metro="4/4" Battito="1" />
# <TEMPO Inizio="156.49136352539062" Bpm="97.89297188430079" Metro="4/4" Battito="1" />
# <TEMPO Inizio="168.74964904785156" Bpm="97.52804251176576" Metro="4/4" Battito="1" />
# <TEMPO Inizio="171.21047973632812" Bpm="98.41841140325629" Metro="4/4" Battito="1" />
# <TEMPO Inizio="178.52618408203125" Bpm="98.19455398670232" Metro="4/4" Battito="1" />
# <TEMPO Inizio="185.8585662841797" Bpm="97.52683304913967" Metro="4/4" Battito="1" />
# <TEMPO Inizio="188.31942749023438" Bpm="98.11053828232454" Metro="4/4" Battito="1" />
# <TEMPO Inizio="207.88919067382812" Bpm="98.16074666034257" Metro="4/4" Battito="1" />
# <TEMPO Inizio="232.33888244628906" Bpm="98.7858899192624" Metro="4/4" Battito="1" />
# <TEMPO Inizio="237.1978759765625" Bpm="98.23630904329985" Metro="4/4" Battito="1" />
# <TEMPO Inizio="256.7425842285156" Bpm="97.527437776703" Metro="4/4" Battito="1" />
# <TEMPO Inizio="259.20343017578125" Bpm="97.85971688534056" Metro="4/4" Battito="1" />
# <TEMPO Inizio="271.46588134765625" Bpm="98.70034356713678" Metro="4/4" Battito="1" />
# <TEMPO Inizio="281.1922912597656" Bpm="98.23646243207794" Metro="4/4" Battito="1" />
# <TEMPO Inizio="290.9646301269531" Bpm="97.527437776703" Metro="4/4" Battito="1" />
# <TEMPO Inizio="295.8863220214844" Bpm="98.17335784932031" Metro="4/4" Battito="1" />
# <TEMPO Inizio="354.55804443359375" Bpm="97.94344569055166" Metro="4/4" Battito="1" />
# <TEMPO Inizio="359.4588317871094" Bpm="98.16637420654297" Metro="4/4" Battito="1" />

tt_orig = [
    7.403456687927246,
    34.28469467163086,
    46.51789093017578,
    51.389488220214844,
    80.7023696899414,
    85.64077758789062,
    124.7510757446289,
    127.1701431274414,
    139.42005920410156,
    154.0764923095703,
    156.49136352539062,
    168.74964904785156,
    171.21047973632812,
    178.52618408203125,
    185.8585662841797,
    188.31942749023438,
    207.88919067382812,
    232.33888244628906,
    237.1978759765625,
    256.7425842285156,
    259.20343017578125,
    271.46588134765625,
    281.1922912597656,
    290.9646301269531,
    295.8863220214844,
    354.55804443359375,
    359.4588317871094,
]

## imported in RekordBox 7.1.3
### Manual Shift to correct grid
# <TEMPO Inizio="0.116" Bpm="98.21" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="34.330" Bpm="98.09" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="46.563" Bpm="98.53" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="51.434" Bpm="98.25" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="80.747" Bpm="97.20" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="81.365" Bpm="97.20" Metro="4/4" Battito="2"/>
# <TEMPO Inizio="85.686" Bpm="98.18" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="121.741" Bpm="98.18" Metro="4/4" Battito="4"/>
# <TEMPO Inizio="124.796" Bpm="99.21" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="127.215" Bpm="97.96" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="139.465" Bpm="98.25" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="154.121" Bpm="99.38" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="156.536" Bpm="97.89" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="168.795" Bpm="97.53" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="171.255" Bpm="98.42" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="178.571" Bpm="98.19" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="185.904" Bpm="97.53" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="188.364" Bpm="98.11" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="207.934" Bpm="98.16" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="232.384" Bpm="98.79" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="237.243" Bpm="98.24" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="256.788" Bpm="97.53" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="259.248" Bpm="97.86" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="271.511" Bpm="98.70" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="281.237" Bpm="98.24" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="291.010" Bpm="97.53" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="295.931" Bpm="98.17" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="341.769" Bpm="98.17" Metro="4/4" Battito="4"/>
# <TEMPO Inizio="354.603" Bpm="97.94" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="359.504" Bpm="98.17" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="391.287" Bpm="98.17" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="405.956" Bpm="98.17" Metro="4/4" Battito="1"/>
# <TEMPO Inizio="420.625" Bpm="98.17" Metro="4/4" Battito="1"/>

tt_shifted = [
    0.116,
    34.330,
    46.563,
    51.434,
    80.747,
    81.365,
    85.686,
    121.741,
    124.796,
    127.215,
    139.465,
    154.121,
    156.536,
    168.795,
    171.255,
    178.571,
    185.904,
    188.364,
    207.934,
    232.384,
    237.243,
    256.788,
    259.248,
    271.511,
    281.237,
    291.010,
    295.931,
    341.769,
    354.603,
    359.504,
    391.287,
    405.956,
    420.625,
]

dt_shift_s2rb7 = mean([
    tt_shifted[1] - tt_orig[1],
    tt_shifted[2] - tt_orig[2],
    tt_shifted[3] - tt_orig[3]
])

# From this data it seems that, to correct the beatgrid from Serato to RB7
# we have to add
# dt_shift_s2rb7 = 0.045 # s

## data from "High Precision" beatgrid.
## Essentially it puts a TEMPO marker on each beat. Taking a couple that
## were present in the original
tt_high_prec = [
    7.450,
    34.340
]

dt_high_pres = mean([
    # paid in full
    tt_high_prec[0] - tt_orig[0],
    tt_high_prec[1] - tt_orig[1],
    # sueno latino
    319.877 - 319.8345947265625,
    0.04823291015622999
    ])

## 0.048121706008909415 -> 0.048

##########################################################
# Encodere

# ## encoder stored in metadata
# ### M4A
# audio_m4a.tags['©too'] # ['Lavf59.16.100'], libavformat from ffmpeg
# # The following describe the algorithm used (from the standard) to encode.
# # This info inform a receiving party how to decode the data.
# audio_m4a.info.codec # 'mp4a.40.2', https://mp4ra.org/registered-types/codecs
# audio_m4a.info.codec_description # 'AAC LC', for display only, may change

# # --> Use audio_m4a.tags['©too'] as description of the encoder

audio_mp3.tags['TSSE']
audio_m4a.tags['©too']
audio_flac.tags.keys()

file_mp3_1 = Path("audio") / "The_Todd_Terry_Project_-_Weekend.mp3"
file_m4a_2 = Path("audio") / "blow-go-reencoded_with_qaac.m4a"
# file_mp3_2 = Path("audio/beautiful_poples.mp3")
file_mp3_3 = Path("audio") / "The_Todd_Terry_Project_-_Weekend-reencoded_with_lame.mp3"
file_mp3_4 = Path('audio') / 'Ultra_Nate_-_Free_(Original_Mix).mp3'
file_mp3_5 = Path('audio') / 'De_Lacy_-_Hideaway_(Deep_Dish_Remix).mp3'

audio_mp3_1: MP3 = mutagen.File(file_mp3, easy=False) # type: ignore[reportUnknownMemberType]
audio_m4a_2 = mutagen.File(file_m4a_2, easy=False)
# audio_mp3_2 = mutagen.File(file_mp3_2, easy=False)
audio_mp3_3 = mutagen.File(file_mp3_3, easy=False)
audio_mp3_3 = mutagen.File(file_mp3_3, easy=False)
audio_mp3_4 = mutagen.File(file_mp3_4, easy=False)
audio_mp3_5 = mutagen.File(file_mp3_5, easy=False)

audio_m4a_2.tags['©too']
# audio_mp3_2.tags['TSSE']

i_1 = audio_mp3_1.info
audio_mp3_1.tags['TSSE']
i_1.encoder_info
i_1.encoder_settings
i_1.bitrate_mode


i_3 = audio_mp3_3.info
# audio_mp3_3.tags['TSSE']
audio_mp3_3.info.encoder_info
audio_mp3_3.info.encoder_settings
audio_mp3_3.info.bitrate_mode

i_4 = audio_mp3_4.info
audio_mp3_4.tags['TSSE']
audio_mp3_4.info.encoder_info
audio_mp3_4.info.encoder_settings
audio_mp3_4.info.bitrate_mode

i_5 = audio_mp3_5.info
audio_mp3_5.tags['TSSE']
audio_mp3_5.info.encoder_info
audio_mp3_5.info.encoder_settings
audio_mp3_5.info.bitrate_mode


a_mp3_2 = from_serato(audio_mp3_2)
a_mp3_3 = from_serato(audio_mp3_3)

################
# 'Free (Original Mix)'

a_4 = from_serato(audio_mp3_4)
m_4 = a_4.markers
bg_4 = a_4.beatgrid
p_sdjpro_4 = bg_4[0].position
# Beatgrid shifted by -13ms!
dt_4 = 0.363 - p_sdjpro_4
      # <TEMPO Inizio="0.363" Bpm="125.00" Metro="4/4" Battito="1"/>

m_4_rb7 = [
    0.376,
    107.896,
    169.336,
    200.056,
    123.256,
]
# <POSITION_MARK Name="64" Type="0" Start="0.376" Num="0" Red="165" Green="225"
#                Blue="22"/>
# <POSITION_MARK Name="32" Type="0" Start="107.896" Num="1" Red="230" Green="40"
#                Blue="40"/>
# <POSITION_MARK Name="hook free" Type="0" Start="169.336" Num="2" Red="224" Green="100"
#                Blue="27"/>
# <POSITION_MARK Name="32" Type="0" Start="200.056" Num="3" Red="230" Green="40"
#                Blue="40"/>
# <POSITION_MARK Name="" Type="4" Start="123.256" End="138.616" Num="7" Red="80"
#                Green="180" Blue="255"/>

# markers are NOT shifted!
dt_m_4 = list(map(lambda a, b: a - b.start, m_4_rb7, m_4))

################
# 'Hideaway (Deep Dish Remix)'

a_5 = from_serato(audio_mp3_5)
m_5 = a_5.markers
bg_5 = a_5.beatgrid
# has 1 BG
p_sdjpro_5 = bg_5[0].position
# Beatgrid shifted by -19ms!
dt_5 = 0.474 - p_sdjpro_5
# <TEMPO Inizio="0.474" Bpm="122.00" Metro="4/4" Battito="1"/>

m_5_rb7 = [
    0.493,
    110.656,
    126.394,
    299.509,
    346.722,
    346.722,
]
# <POSITION_MARK Name="4 x 32" Type="0" Start="0.493" Num="0" Red="40" Green="226"
#                Blue="20"/>
# <POSITION_MARK Name="32" Type="0" Start="110.656" Num="1" Red="40" Green="226"
#                Blue="20"/>
# <POSITION_MARK Name="I need a man" Type="0" Start="126.394" Num="2" Red="48"
#                Green="90" Blue="255"/>
# <POSITION_MARK Name="" Type="0" Start="299.509" Num="3" Red="224" Green="100"
#                Blue="27"/>
# <POSITION_MARK Name="" Type="0" Start="346.722" Num="4" Red="230" Green="40"
#                Blue="40"/>
# <POSITION_MARK Name="" Type="4" Start="346.722" End="362.460" Num="7" Red="80"
#                Green="180" Blue="255"/>

# markers are NOT shifted!
dt_m_5 = list(map(lambda a, b: a - b.start, m_5_rb7, m_5))

##########################################################
# Traktor

from djbabel.traktor.write import info_tag, entry_tag, album_tag, modification_info_tag, tempo_tag, musical_key_tag, loudness_tag, location_tag, cue_v2_beatgrid, cue_v2_markers, to_traktor_playlist

file_mp3_4 = Path('audio') / 'Ultra_Nate_-_Free_(Original_Mix).mp3'
file_mp3_5 = Path('audio') / 'De_Lacy_-_Hideaway_(Deep_Dish_Remix).mp3'

audio_mp3_4 = mutagen.File(file_mp3_4, easy=False)
audio_mp3_5 = mutagen.File(file_mp3_5, easy=False)

a1 = from_serato(audio_mp3)
a_flac = from_serato(audio_flac)
a_m4a = from_serato(audio_m4a)
a4 = from_serato(audio_mp3_4)
a5 = from_serato(audio_mp3_5)

trans = ATransformation(parse_input_format('sdjpro'),
                        parse_output_format('traktor4'))

itag = info_tag(a1, trans)
etag = entry_tag(a1, trans)
atag = album_tag(a1, trans)
mtag = modification_info_tag(a1, trans)
ttag = tempo_tag(a1, trans)
ktag = musical_key_tag(a1, trans)
ltag = loudness_tag(a1, trans)
ctag = location_tag(a1, trans)
btag = cue_v2_beatgrid(a1.beatgrid[0])
cuetag = cue_v2_markers(a1.markers[0])

apl = APlaylist("party", [a1, a_flac, a_m4a, a4, a5])
to_traktor_playlist(apl, Path("pl_traktor.nml"), trans)

##########################################################
# battito

from djbabel.rekordbox.write import rb_battito, adjust_time

file_mp3_6 = Path('audio') / '2-01-Paid_in_Full.m4a'
audio_mp3_6 = mutagen.File(file_mp3_6, easy=False)
a6 = from_serato(audio_mp3_6)

trans = ATransformation(parse_input_format('sdjpro'),
                        parse_output_format('rb7'))


new_a6 = adjust_time(a6, trans)
for i, m in enumerate(new_a6.beatgrid):
    battito = rb_battito(new_a6.beatgrid, i)
    print(f"track {a6.title}: bpm: {m.bpm}, battito: {battito}")

for i, m in enumerate(a6.beatgrid):
    battito = rb_battito(a6.beatgrid, i)
    print(f"track {new_a6.title}: bpm: {m.bpm}, battito: {battito}")

for i, m in enumerate(a1.beatgrid):
    battito = rb_battito(a1.beatgrid, i)
    print(f"track {a1.title}: battito: {battito}")

##########################################################
# Traktor NML read

from datetime import datetime

from djbabel.traktor.read import find_collection_entry, from_traktor, get_str_attr, is_entry_tag_attr, get_tag_attr, is_album_tag_attr, get_album_subtag, is_info_tag_attr, get_info_subtag, traktor_attr_name, get_album_subtag, is_musical_key_attr, to_date, get_location, to_bool, get_cue_v2_beatgrid, get_cue_v2_cues, get_loudness, read_traktor_playlist

trans = ATransformation(parse_input_format('traktor4'),
                        parse_output_format('rb7'))

nml_tree = ET.parse('nml/test.nml')
nml_root = nml_tree.getroot()
nml_col = nml_root.find('COLLECTION')

pls = nml_root.findall('.//NODE[@TYPE="PLAYLIST"]')
pl = pls[0]
pl_keys = pl.findall('./PLAYLIST/ENTRY/PRIMARYKEY')

e0 = find_collection_entry(nml_col, pl_keys[0].get('KEY'))
e1 = find_collection_entry(nml_col, pl_keys[1].get('KEY'))

t0_title = get_str_attr('title', e0)

e0_cues = e0.findall('./CUE_V2[@TYPE!="4"]')

e0_bg = get_cue_v2_beatgrid(e0)
e0_cues = get_cue_v2_cues(e0)

e0_ldns = get_loudness(e0)

at0 = from_traktor(e0, 20)
at1 = from_traktor(e1, 20)

apl = read_traktor_playlist(Path('nml/test.nml'), 'test', trans)

apl_rel = read_traktor_playlist(Path('nml/test.nml'), 'test', trans, Path('/mnt'), Path('/Users/beffa'))

##########################################################

file_name = 'Anna Naklab/Supergirl (feat. Alle Farben & Younotus) - EP/01 Supergirl (feat. Alle Farben & Younotus) [Radio Edit].m4a'

file_db = Path('serato_write_tests') / 'after_wriring_tags_with_djbabel' / file_name
audio_db = mutagen.File(file_db, easy=False)

file_serato = Path('serato_write_tests') / 'after_using_in_serato' / file_name
audio_serato = mutagen.File(file_serato, easy=False)

mv2_db = get_serato_markers_v2(audio_db)
mv2_serato = get_serato_markers_v2(audio_serato)

bg_db = get_serato_beatgrid(audio_db)
bg_serato = get_serato_beatgrid(audio_serato)

bg_stag = SeratoTags.BEATGRID.value.names[AFormat.M4A]
bg_db_raw = audio_db.tags[bg_stag]
bg_db_bytes = parse_serato_envelope(bg_db_raw[0], SeratoTags.BEATGRID.value.marker)

bg_serato_raw = audio_serato.tags[bg_stag]
bg_serato_bytes = parse_serato_envelope(bg_serato_raw[0], SeratoTags.BEATGRID.value.marker)

file_de = Path('audio') / 'De_Lacy_-_Hideaway_(Deep_Dish_Remix).mp3'
audio_de = mutagen.File(file_de, easy=False)
# Footer(65)

file_pif = Path('audio') / '2-01-Paid_in_Full.m4a'
audio_pif = mutagen.File(file_pif, easy=False)
# Footer(109) ???

# file_mp3_ref = Path("audio") / "crate_write_test_ref.mp3"
# file_flac_ref = Path("audio") / "crate_write_test_ref.flac"
# file_m4a_ref = Path("audio") / "crate_write_test_ref.m4a"

# audio_mp3_ref = mutagen.File(file_mp3_ref, easy=False) # pyright: ignore
# audio_flac_ref = mutagen.File(file_flac_ref, easy=False) # pyright: ignore
# audio_m4a_ref = mutagen.File(file_m4a_ref, easy=False) # pyright: ignore

##########################################################
# RekordBox read

from datetime import datetime
from djbabel.rekordbox.read import read_rekordbox_playlist, get_color
from urllib.request import url2pathname
from urllib.parse import urlparse
from djbabel.serato.read import parse_color

trans = ATransformation(parse_input_format('traktor4'),
                        parse_output_format('traktor4'))

rb_file = Path('rb7xml/test.xml')
rb_tree = ET.parse(rb_file)

relative = Path('/C:/Users/beffa/src/djbabel/tests/')
apl = read_rekordbox_playlist(rb_file, "my_playlist", trans, Path(''), relative)

url = "file://localhost/C%3A/Users/beffa/src/djbabel/tests/audio/The_Todd_Terry_Project_-_Weekend-reencoded_with_lame.mp3"

url2pathname(url)

parsed_url = urlparse(url)

url2pathname(parsed_url.path)

##########################################################

# Local Variables:
# python-shell-interpreter: "ipython"
# python-shell-interpreter-args: "--simple-prompt"
# End:
