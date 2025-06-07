from dataclasses import dataclass
from enum import Enum
from ..types import AFormat

############################################################
# Audio file metadata tags

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

    # PLAYCOUNT = STag({
    #     AFormat.MP3 : 'TXXX:SERATO_PLAYCOUNT',
    #     # base64 endoded number with footer
    #     # example b'0\x00\xd1\xb6\xb6\xa4\x90'
    #     AFormat.M4A : '----:com.serato.dj:playcount',
    #     AFormat.FLAC : 'serato_playcount' # just a number (no prefix), e.g. b'0'
    # },
    #                    b'')

    ANALYSIS = STag({
        AFormat.MP3 : 'GEOB:Serato Analysis',
        AFormat.M4A : '----:com.serato.dj:analysisVersion',
        AFormat.FLAC : 'serato_analysis'
    },
                    b'Serato Analysis')

    # VIDEOASSOC = STag({
    #     AFormat.MP3 : '',
    #     AFormat.M4A : '----:com.serato.dj:videoassociation',
    #     AFormat.FLAC : 'serato_video_assoc'
    # },
    #                 b'Serato VidAssoc')

    RELVOL = STag({
        AFormat.MP3 : 'RVA2:SeratoGain',
        AFormat.M4A : '----:com.serato.dj:relvol',
        AFormat.FLAC : 'serato_relvol'
    },
                    b'Serato RelVolAd')

############################################################
# Metadata Base

class EntryBase(object):
    FIELDS: tuple = ()
    def __init__(self, *args):
        assert len(args) == len(self.FIELDS)
        for field, value in zip(self.FIELDS, args):
            setattr(self, field, value)

    def __repr__(self):
        return '{name}({data})'.format(
            name=self.__class__.__name__,
            data=', '.join('{}={!r}'.format(name, getattr(self, name))
                           for name in self.FIELDS))
