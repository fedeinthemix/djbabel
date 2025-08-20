# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from ..types import (
    AFormat,
    AMarkerType
)


#######################################################################
# Mappings

# includes mapping of fields from ATrack to the Rekordbox XML name of
# only those fields whose mapping is not a simple conversion to
# CamelCase. The later are mapped via a function.
REKORDBOX_FIELD_NAMES_MAP = {
    'title' : 'Name',
    # 'artist',
    # 'composer',
    # 'album',
    # 'grouping',
    # 'genre',
    'aformat' : 'kind',
    # 'size',
    # 'total_time',
    # 'disc_number',
    # 'track_number',
    'release_date' : 'Year',
    # 'average_bpm',
    # 'date_added',
    # 'bit_rate',
    # 'sample_rate',
    # 'comments',
    # 'play_count',
    # 'rating',
    # 'location',
    # 'remixer',
    # 'tonality',
    # 'label',
    # 'mix',
    # 'data_source',
    # 'markers',
    # 'beatgrid',
    # 'locked',
    'color' : 'Colour',
    'trackID' : 'TrackID',
    # 'loudness'
}

# Map AMarkerType into the corresponding Rekordbox number
REKORDBOX_MARKERTYPE_MAP = {
    AMarkerType.CUE : "0",
    AMarkerType.FADE_IN : "1",
    AMarkerType.FADE_OUT : "2",
    AMarkerType.CUE_LOAD : "3",
    AMarkerType.LOOP : "4"
}

# Mapping from AFormat to Rekordbox string.
REKORDBOX_AFORMAT_MAP = {
    AFormat.MP3 : 'MP3 File',
    AFormat.FLAC : 'FLAC File',
    AFormat.M4A : 'MP4 File',
    # AFormat.WAV : 'WAV FILE',
}

#######################################################################

def rb_attr_name(s: str) -> str:
    """Convert an ATrack field name (as a string) into the name used by Rekordbox.
    """
    if s in REKORDBOX_FIELD_NAMES_MAP.keys():
        return REKORDBOX_FIELD_NAMES_MAP[s]
    else:
        return ''.join(map(lambda w: w.capitalize(), s.split('_')))

