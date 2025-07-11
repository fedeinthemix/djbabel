# In ipython run
# %load_ext autoreload
# %autoreload 2

import functools
import sys
sys.path.append('../src')

from datetime import date
from pathlib import Path, PureWindowsPath
import warnings
import os
import string
import io

# from typing import cast

from mutagen.id3 import ID3, PRIV
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
from djbabel.serato.markers2 import CueEntry, get_serato_markers_v2, ColorEntry, BpmLockEntry
from djbabel.serato.utils import audio_file_type, readbytes, serato_metadata
from djbabel.serato.types import STag, SeratoTags, EntryBase
from djbabel.serato.autotags import get_serato_autotags
from djbabel.serato.overview import get_serato_overview
from djbabel.serato.beatgrid import get_serato_beatgrid
from djbabel.serato.markers import get_serato_markers
from djbabel.serato.analysis import get_serato_analysis
from djbabel.serato.relvol import get_serato_relvol

from djbabel.serato.utils import serato_metadata, parse_serato_envelope, serato_tag_marker, serato_tag_name, audio_file_type, maybe_metadata, get_serato_metadata
from djbabel.types import ABeatGridBPM, ADataSource, AFormat, AMarkerType, AMarker, APlaylist, ASoftware, ATrack, ABeatGridBPM, ALoudness, ATransformation

from djbabel.serato import from_serato, read_serato_playlist

from djbabel.serato.crate import CrateFieldKind, take_field, take_field_type, parse_field_bool, Unknown, take_fields, created_classes, get_track_paths

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

from djbabel.traktor.utils import traktor_path

fn = Path('subcrates') / 'FEBE_MIX_80_90.crate'

wp = PureWindowsPath('C:\\Users\\beffa\\test.m4a')
anchor = Path('/run/media/beffa/FBE\\ HDD\\ 1/backups/orione-backpc-windows/')
relative = Path('Users/beffa')
pl = read_serato_playlist(fn, anchor, relative)

with open(fn, "rb") as f:
    data = f.read()

fp = io.BytesIO(data)
flds = take_fields(fp)
get_track_paths(flds)

##########################################################
# REkordbox

from djbabel.rekordbox import to_rekordbox_playlist

a1 = from_serato(audio_mp3)
a_flac = from_serato(audio_flac)
a_m4a = from_serato(audio_m4a)

trans = ATransformation(parse_input_format('sdjpro'),
                        parse_output_format('rb7'))

apl = APlaylist("party", [a1, a_flac, a_m4a])
to_rekordbox_playlist(apl, Path("test_rekordbox.xml"), trans)

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

# file_mp3 = Path("audio") / "The_Todd_Terry_Project_-_Weekend.mp3"
file_m4a_2 = Path("audio") / "blow-go-reencoded_with_qaac.m4a"
file_mp3_2 = Path("audio/beautiful_poples.mp3")
file_mp3_3 = Path("audio") / "The_Todd_Terry_Project_-_Weekend-reencoded_with_lame.mp3"

# audio_mp3: MP3 = mutagen.File(file_mp3, easy=False) # type: ignore[reportUnknownMemberType]
audio_m4a_2 = mutagen.File(file_m4a_2, easy=False)
audio_mp3_2 = mutagen.File(file_mp3_2, easy=False)
audio_mp3_3 = mutagen.File(file_mp3_3, easy=False)

audio_m4a_2.tags['©too']
audio_mp3_2.tags['TSSE']
audio_mp3_3.info.encoder_info
audio_mp3_3.info.encoder_settings

a_mp3_2 = from_serato(audio_mp3_2)
a_mp3_3 = from_serato(audio_mp3_3)

##########################################################
# Traktor

from djbabel.traktor.write import info_tag, entry_tag, album_tag, modification_info_tag, tempo_tag, musical_key_tag, loudness_tag, location_tag, cue_v2_beatgrid, cue_v2_markers, to_traktor_playlist

a1 = from_serato(audio_mp3)
a_flac = from_serato(audio_flac)
a_m4a = from_serato(audio_m4a)

trans = ATransformation(parse_input_format('sdjpro'),
                        parse_output_format('rb7'))

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

apl = APlaylist("party", [a1, a_flac, a_m4a])
to_traktor_playlist(apl, Path("test_traktor.nml"), trans)

##########################################################

# Local Variables:
# python-shell-interpreter: "ipython"
# python-shell-interpreter-args: "--simple-prompt"
# End:
