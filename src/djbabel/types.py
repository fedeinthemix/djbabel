from datetime import date
from pathlib import Path
from enum import StrEnum, auto
from dataclasses import dataclass, fields

class AFormat(StrEnum):
    """Supported audio file formats.
    """
    MP3 = auto()
    M4A = auto()
    FLAC = auto()

@dataclass
class ABeatGridBPM:
    position: float
    bpm: float

@dataclass
class ABeatGrid:
    changes: list[ABeatGridBPM]
    
class AMarkerType(StrEnum):
    CUE = auto()
    CUE_LOAD = auto()
    LOOP = auto()

@dataclass
class AMarker:
    name: str
    color: tuple[int, int, int] | None
    start: float
    end: float | None
    kind: AMarkerType
    index: int # which hotcue pad
    locked: bool # used, e.g., by loops in Serato DJ

# class AMarkers:
#     markers: list[AMarker]
#     def __init__(self, ms):
#         self.markers = ms

# set Serato gaindb=0.0, Traktor PEAK_DB="-0"
#
# Serato 'autogain' and Traktor PERCEIVED_DB seems to match well.
# Currently only tested on MARS, Pump Up The Volume.
# Check more tracks
@dataclass
class ALoudness:
    autogain: float # Serato autogain, or Traktor PERCEIVED_DB ANALYZED_DB
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
    size: int 
    total_time: float
    disc_number: int | None
    track_number: int | None
    # year: int | None
    release_data : date | None
    average_bpm: float | None
    date_added: date | None
    bit_rate: int # bps
    sample_rate: float # Hz
    comments: str | None
    play_count: int | None
    rating: int | None
    location: Path
    remixer: str | None
    tonality: str | None
    label: str | None
    mix: str | None
    data_source: ADataSource
    markers: list[AMarker] | None = None
    beatgrid: ABeatGrid | None = None
    locked: bool = True
    color: tuple[int, int, int] | None = None # track display colors (e.g. in Serato)
    trackID: int | None = None # How to set? Can we leave it empty in RekordBox?
    loudness: ALoudness | None = None
