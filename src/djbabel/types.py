from datetime import date
from pathlib import Path
from enum import StrEnum, auto

class AFormat(StrEnum):
    """Supported audio file formats.
    """
    MP3 = auto()
    M4A = auto()
    FLAC = auto()

class ABeatGrid:
    position: int # or float?
    beats: int # to next marker
    bpm: float | None # forat for last one, otherwise None
    last: bool
    
class AMarkerType(StrEnum):
    CUE = auto()
    LOOP = auto()
    
class AMarkers:
    name: str
    color: None | int # int -> RGB or similar
    start: float
    end: float | None
    kind: AMarkerType
    index: int # which hotcue pad
    locked: bool

class ATrack:
    trackID: int | None # How to set? Can we leave it empty in RekordBox?
    title: str
    artist: str
    composer: str | None
    album: str | None
    Grouping: str | None
    genre: str | None
    aformat: AFormat
    size: int 
    total_time: float
    disc_number: int | None
    track_number: int | None
    year: int | None
    average_bpm: float | None
    date_added: date | None
    bit_rate: float # kbps
    sample_rate: float # Hz
    comments: str | None
    play_count: int | None
    rating: int | None
    location: Path
    remixer: str | None
    tonality: str | None
    label: str | None
    mix: str | None
    beatgrid: ABeatGrid | None
    beatgridLocked: bool = False
    markers: AMarkers | None

