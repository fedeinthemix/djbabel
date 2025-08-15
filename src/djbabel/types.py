# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import date
from pathlib import Path
from enum import Enum, IntEnum, StrEnum, auto
from dataclasses import dataclass, field

###################################################################

class AFormat(StrEnum):
    """Supported audio file formats.
    """
    MP3 = auto()
    M4A = auto()
    FLAC = auto()

# The beatgrid position time for a given beat is not identical in the
# various softwares.  For example, given a beatgrid prepared with
# Serato DJ Pro 3.3.2, when I convert it to a Rekordbox 7.1.3 XML
# file, the beatgrid is shifted. An analysis of 2 files suggests that
# to the Serato positions, to get a good grid in RB7 we have to add
# dt=0.048 s.
#
# Given the dt sfrom Serato to each other software, we should be able
# to compute the dt for an arbitrary conversion as:
#
# dt_traktor_to_rb7 = -dt_s_to_traktor + dt_s_to_rb7
#
# Note: dt_Y_to_X = -dt_X_to_Y.
#
# The positions in the ABeatGridBPM class can therefore be normalized
# to the Serato values at import time (-dt_s_to_source_format). At
# export time, we then simply convert from Serato to the export format
# (dt_s_to_target_format).
#
# Actually, as reference we should use the more accurate software: RB7
# or Traktor 4?
@dataclass
class ABeatGridBPM:
    position: float # [s]
    bpm: float
    metro: tuple[int,int] = (4,4)

class AMarkerType(StrEnum):
    CUE = auto()
    CUE_LOAD = auto()
    LOOP = auto()
    FADE_IN = auto()
    FADE_OUT = auto()

class AMarkerColors(Enum):
    """16 Cue colors (taken from Serato DJ Pro).

    The various DJ Software offer a palette to color cue points. It
    seems that if we spcecify a color not in the palette, the color
    may not be reproduced correctly (e.g., exporting Rekordbox
    playlists to CDJs). Hence, we define a palette and convert colors
    to the closest (as perceived by humans) in this palette. We chose
    a subset of 16 colors from Serato DJ Pro as these are
    distinguishable colors (as opposed to some other software
    palettes).

    When we generate a playlist for a piece of software, we map this
    discrete palette to the closest color in its palette.

    """
    RED = (204, 0, 0)
    RED_ORANGE =  (204, 68, 0)
    ORANGE =  (204, 136, 0)
    YELLOW =  (204, 204, 0)
    LIME_gREEN =  (136, 204, 0)
    DARK_GREEN =  (68, 204, 0)
    BRIGHT_GREEN =  (0, 204, 0)
    LIGHT_GREEN =  (0, 204, 68)
    TEAL =  (0, 204, 136)
    CYAN =  (0, 204, 204)
    SKY_BLUE =  (39, 170, 225) # Serato Loop color. (Previous value (0, 136, 204))
    BLUE =  (0, 68, 204) # DARK_CYAN
    DARK_BLUE =  (0, 0, 204)
    # INDIGO =  (68, 0, 204)
    VIOLET =  (136, 0, 204)
    MAGENTA =  (204, 0, 204)
    HOT_PING =  (204, 0, 136)
    # CRIMSON =  (204, 0, 68)

# Marker start and end also have to be normalized and shifted as
# ABeatGridBPM position.
@dataclass
class AMarker:
    name: str
    color: AMarkerColors | None # RGB
    start: float # [s]
    end: float | None # [s]
    kind: AMarkerType
    index: int # which hotcue pad
    locked: bool # used, e.g., by loops in Serato DJ

# set Serato gaindb=0.0, Traktor PEAK_DB="-0"
#
# Serato 'autogain' and Traktor PERCEIVED_DB seems to match well.
# Currently only tested on MARS, Pump Up The Volume.
# Check more tracks
@dataclass
class ALoudness:
    autogain: float # Serato autogain, or Traktor PERCEIVED_DB, ANALYZED_DB
    gain_db: float = 0.0 # user mixer gain setting

class ASoftware(StrEnum):
    SERATO_DJ_PRO = auto()
    REKORDBOX = auto()
    TRAKTOR = auto()

class AEncoderMode(IntEnum):
    UNKNOWN = auto()
    CBR = auto()
    VBR = auto()
    ABR = auto()

# Information that may be useful in setting a beatgrid shift.
# 'bitrate' and 'sample_rate' are in ATrack.
@dataclass
class AEncoder:
    text: str
    settings: str = ''
    mode: AEncoderMode = AEncoderMode.UNKNOWN

# version is the number in the Serato Marker2 analisys tag. However,
# the meaning of this value is unclear ([2,1] for MP3 and [0,1,0] for
# FLAC and M4A).
#
# Currently versioin is unused.
#
# software is used by:
#
# - rb_attr_color: to verify if source and target are the same. Will
#                  ever be useful?
#
# - rb_reindex_loops: to check if marker indices come from Serato DJ
#                     Pro which uses different index-spaces for cues
#                     and from loops while other programs use the same.
@dataclass
class ADataSource:
    software: ASoftware
    version: list[int] # data format version
    encoder: AEncoder | None = None # None means that it's
                                    # unspecified. This is usefule for
                                    # example in loss-less.

@dataclass
class AFlags:
    beatgrid_locked: bool


@dataclass
class ATrack:
    title: str | None
    artist: str | None
    composer: str | None
    album: str | None
    grouping: str | None
    genre: str | None
    aformat: AFormat
    size: int | None # number of bytes
    total_time: float | None # [s]
    disc_number: int | None
    track_number: int | None
    release_date : date | None
    average_bpm: float | None
    date_added: date | None
    bit_rate: int | None # [bps]
    sample_rate: float | None # [Hz]
    comments: str | None
    play_count: int | None
    rating: int | None # 0 to 255, see Note (1)
    location: Path
    remixer: str | None
    tonality: str | None # Classic notation, e.g., 'Bbmaj'
    label: str | None
    mix: str | None
    data_source: ADataSource
    markers: list[AMarker] = field(default_factory=list)
    beatgrid: list[ABeatGridBPM] = field(default_factory=list)
    locked: bool = True # file analysis locked
    color: tuple[int, int, int] | None = None # track display color
    trackID: int | None = None # RekordBox: trackID, Traktor: AUDIO_ID
    loudness: ALoudness | None = None
    # flags: AFlags | None = None

# ATrack Notes:
#
# (1): Traktor and RekordBox have 0 to 5 stars. They both convert to the same int
#      1 : "51", 2 : "102", 3 : "153", 4 : "204", 5 : "255"
#      Serato doesn't have a rating feature.


@dataclass
class APlaylist:
    name: str
    entries: int # number of tracks
    tracks: list[ATrack]

    def __init__(self, name, tracks):
        self.name = name
        self.tracks = tracks
        self.entries = len(tracks)

@dataclass
class ASoftwareInfo:
    """CLI Specification of source/target DJ software.
    """
    software: ASoftware
    version: tuple[int,int,int]

@dataclass
class ATransformation:
    """The playlist transformation being performed.
    """
    source: ASoftwareInfo
    target: ASoftwareInfo
