from dataclasses import dataclass
from enum import Enum
from ..types import AFormat

@dataclass
class STag:
    names: dict[AFormat, str]
    marker: bytes

class SeratoTags(Enum):
    AUTOTAGS = STag({
        AFormat.MP3 : 'GEOB:Serato Autotags',
        AFormat.M4A : '----:com.serato.dj:autgain',
        AFormat.FLAC : 'serato_autogain'
    },
                    b'Serato Autotags')

    BEATGRID = STag({
        AFormat.MP3 : 'GEOB:Serato BeatGrid',
        AFormat.M4A : '----:com.serato.dj:beatgrid',
        AFormat.FLAC : 'serato_beatgrid'
    },
                    b'Serato BeatGrid')

    MARKERS = STag({
        AFormat.MP3 : 'GEOB:Serato Markers_',
        AFormat.M4A : '----:com.serato.dj:markers',
        AFormat.FLAC : 'serato_markers'
    },
                   b'Serato Markers_')
    
    MARKERS2 = STag({
        AFormat.MP3 : 'GEOB:Serato Markers2',
        AFormat.M4A : '----:com.serato.dj:markersv2',
        AFormat.FLAC : 'serato_markers_v2'
    },
                    b'Serato Markers2')

    OVERVIEW = STag({
        AFormat.MP3 : 'GEOB:Serato Overview',
        AFormat.M4A : '----:com.serato.dj:overview',
        AFormat.FLAC : 'serato_overview'
    },
                    b'Serato Overview')
