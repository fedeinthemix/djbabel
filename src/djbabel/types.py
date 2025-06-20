from datetime import date
from pathlib import Path
from enum import StrEnum, auto
from dataclasses import dataclass, field

class AFormat(StrEnum):
    """Supported audio file formats.
    """
    MP3 = auto()
    M4A = auto()
    FLAC = auto()

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

@dataclass
class AMarker:
    name: str
    color: tuple[int, int, int] | None # RGB
    start: float # [ms]
    end: float | None # [ms]
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

@dataclass
class ADataSource:
    software: ASoftware
    version: list[int] # data format version

@dataclass
class ATrack:
    title: str | None
    artist: str | None
    composer: str | None
    album: str | None
    grouping: str | None
    genre: str | None
    aformat: AFormat
    size: int # number of bytes
    total_time: float # [s]
    disc_number: int | None
    track_number: int | None
    release_date : date | None
    average_bpm: float | None
    date_added: date | None
    bit_rate: int # [bps]
    sample_rate: float # [Hz]
    comments: str | None
    play_count: int | None
    rating: int | None # 0 to 5 stars
    location: Path
    remixer: str | None
    tonality: str | None # Classic notation, e.g., 'Bbmaj'
    label: str | None
    mix: str | None
    data_source: ADataSource
    markers: list[AMarker] = field(default_factory=list)
    beatgrid: list[ABeatGridBPM] = field(default_factory=list)
    locked: bool = True
    color: tuple[int, int, int] | None = None # track display colors (e.g. in Serato)
    trackID: int | None = None # REMOVE!! Not necessary. How to set? Can we leave it empty in RekordBox?
    loudness: ALoudness | None = None

@dataclass
class APlaylist:
    name: str
    entries: int # number of tracks
    tracks: list[ATrack]

    def __init__(self, name, tracks):
        self.name = name
        self.tracks = tracks
        self.entries = len(tracks)
