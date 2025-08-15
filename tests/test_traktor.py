# SPDX-FileCopyrightText: NONE
#
# SPDX-License-Identifier: CC0-1.0

from datetime import date
from pathlib import Path, PurePosixPath, PureWindowsPath
import pytest
import xml.etree.ElementTree as ET

from djbabel.traktor.read import aformat_from_path
from djbabel.traktor.utils import traktor_path

from djbabel.traktor.write import (
    info_tag,
    entry_tag,
    album_tag,
    modification_info_tag,
    tempo_tag,
    musical_key_tag,
    loudness_tag,
    location_tag,
    cue_v2_beatgrid,
    cue_v2_markers,
    to_traktor_playlist,
    entry_tag
)

from djbabel.traktor.read import (
    find_collection_entry,
    get_info_subtag,
    get_album_subtag,
    get_tempo_subtag,
    get_location,
    get_loudness,
    adjust_location,
    get_musical_key_subtag,
    musical_key_to_classic_key,
    get_cue_v2_beatgrid,
    get_cue_v2_cues,
    read_traktor_playlist
)

from djbabel.types import (
    ABeatGridBPM,
    ADataSource,
    AFormat,
    ALoudness,
    AMarker,
    ASoftware,
    ASoftwareInfo,
    ATrack,
    ATransformation,
    AMarkerType,
    AMarkerColors
)

from djbabel.utils import path_anchor, to_float

###############################################################
# Write NML files

class TestTraktorWriteTags:
    # At the moment we don't test 'location_tag' and 'entry_tag' as
    # they need to access the Windows/macOS filesystem.
    
    trans = ATransformation(ASoftwareInfo(ASoftware.SERATO_DJ_PRO, (3,2,3)),
                            ASoftwareInfo(ASoftware.TRAKTOR, (4,2,0)))

    @pytest.mark.parametrize("path, expected", [
        (PurePosixPath('/tmp') / 'beautiful_poples.mp3', '/:tmp/:beautiful_poples.mp3'),
        (PureWindowsPath('C:\\tmp') / 'beautiful_poples.mp3', '/:tmp/:beautiful_poples.mp3'),
    ])
    def test_traktor_path(self, path, expected):
        result = traktor_path(path)
        assert result == expected


    def test_traktor_info_tag(self, atrack_input_1):
        result = info_tag(atrack_input_1, self.trans)
        assert result.attrib == {'FLAGS': '28',
                                 'COMPOSER': 'composer',
                                 'GENRE': 'genre',
                                 'FILESIZE': '12',
                                 'PLAYTIME': '1',
                                 'PLAYTIME_FLOAT': '1.0',
                                 'RELEASE_DATE': '2025/01/01',
                                 'IMPORT_DATE': '2025/01/02',
                                 # 'BITRATE': '320', # we let Traktor calculate it
                                 'COMMENT': 'comments',
                                 'RATING': '255',
                                 'REMIXER': 'remixer',
                                 # 'KEY': 'Bmaj', # now use MUSICAL_KEY tag
                                 'LABEL': 'label'}


    def test_traktor_album_tag(self, atrack_input_1):
        result = album_tag(atrack_input_1, self.trans)
        assert result.attrib == {'TITLE': 'album', 'DISC_NUMBER': '0', 'TRACK': '2'}


    def test_traktor_modification_info_tag(self, atrack_input_1):
        result = modification_info_tag(atrack_input_1, self.trans)
        assert result.attrib == {'AUTHOR_TYPE': 'user'}


    def test_traktor_tempo_tag(self, atrack_input_1):
        result = tempo_tag(atrack_input_1, self.trans)
        assert result.attrib == {'BPM_QUALITY': '100.000000', 'BPM': '120.0'}


    def test_traktor_musical_key_tag(self, atrack_input_1):
        result = musical_key_tag(atrack_input_1, self.trans)
        assert result.attrib == {'VALUE': '6'}

    def test_traktor_loudness_tag(self, atrack_input_1):
        result = loudness_tag(atrack_input_1, self.trans)
        assert result.attrib == {'ANALYZED_DB': '5.0', 'PERCEIVED_DB': '5.0'}


    def test_traktor_cue_v2_beatgrid_tag(self, atrack_input_1):
        result = cue_v2_beatgrid(atrack_input_1.beatgrid[0])
        assert result.attrib == {'NAME': 'Beat Marker',
                                 'TYPE': '4',
                                 'START': '40.0',
                                 'LEN': '0.0',
                                 'HOTCUE': '-1',
                                 'REPEATS': '-1',
                                 'DISPL_ORDER': '0'}


    def test_traktor_cue_v2_beatgrid_tag_grid(self, atrack_input_1):
        result = cue_v2_beatgrid(atrack_input_1.beatgrid[0])
        assert result[0].attrib == {'BPM': '120.4'}
        assert result[0].tag == 'GRID'


    def test_traktor_cue_v2_markers_tag(self, atrack_input_1):
        result = cue_v2_markers(atrack_input_1.markers[0])
        assert result.attrib == {'NAME': '32',
                                 'TYPE': '0',
                                 'START': '1000.0',
                                 'LEN': '0.0',
                                 'HOTCUE': '0',
                                 'REPEATS': '-1',
                                 'DISPL_ORDER': '0'}


    def test_traktor_entry_tag(self, atrack_input_1):
        result = entry_tag(atrack_input_1, self.trans)
        assert result.attrib['ARTIST'] == 'artist'
        assert result.attrib['AUDIO_ID'] == ''
        assert result.attrib['LOCK'] == '1'
        # 'LOCK_MODIFICATION_TIME' is set to the current time.
        assert 'LOCK_MODIFICATION_TIME' in result.attrib.keys()


###############################################################
# Read NML files

class TestTraktorReadTags:
    
    trans = ATransformation(ASoftwareInfo(ASoftware.TRAKTOR, (4,2,0)),
                            ASoftwareInfo(ASoftware.TRAKTOR, (4,2,0)))


    nml_path = Path('tests') / 'nml' / 'test.nml'
    root = ET.parse(nml_path).getroot()
    col = root.find('COLLECTION')
    assert col is not None
    pl = root.find('.//NODE[@TYPE="PLAYLIST"]')
    assert pl is not None
    pl_keys = pl.findall('./PLAYLIST/ENTRY/PRIMARYKEY')
    e0 = find_collection_entry(col, pl_keys[0].get('KEY'))
    e1 = find_collection_entry(col, pl_keys[1].get('KEY'))


    @pytest.mark.parametrize("path, expected", [
        (PurePosixPath('/tmp') / 'beautiful_poples.mp3', AFormat.MP3),
        (PurePosixPath('/tmp') / 'beautiful_poples.MP3', AFormat.MP3),
        (PurePosixPath('/tmp') / 'beautiful_poples.flac', AFormat.FLAC),
        (PurePosixPath('/tmp') / 'beautiful_poples.FLAC', AFormat.FLAC),
        (PurePosixPath('/tmp') / 'beautiful_poples.m4a', AFormat.M4A),
        (PurePosixPath('/tmp') / 'beautiful_poples.M4A', AFormat.M4A),
        (PurePosixPath('/tmp') / 'beautiful_poples.aac', AFormat.M4A),
        (PurePosixPath('/tmp') / 'beautiful_poples.AAC', AFormat.M4A),
        (PurePosixPath('/tmp') / 'beautiful_poples.mp4', AFormat.M4A),
        (PurePosixPath('/tmp') / 'beautiful_poples.MP4', AFormat.M4A),
    ])
    def test_traktor_aformat_from_path(self, path, expected):
        result = aformat_from_path(path)
        assert result == expected


    @pytest.mark.parametrize("fn, expected", [
        ('bit_rate', '320000'),
        ('genre', "Dance / Pop"),
        ('not_defined', None),
    ])
    def test_traktor_get_info_subtag(self, fn, expected):
        assert self.e0 is not None
        result = get_info_subtag(fn, self.e0)
        assert result == expected


    @pytest.mark.parametrize("fn, expected", [
        ('track_number', '1'),
        ('album', "Beautiful People (Extended)"),
        ('not_defined', None),
    ])
    def test_traktor_get_album_subtag(self, fn, expected):
        assert self.e0 is not None
        result = get_album_subtag(fn, self.e0)
        assert result == expected


    @pytest.mark.parametrize("fn, expected", [
        ('average_bpm', 126.999878),
        ('not_defined', None),
    ])
    def test_traktor_get_tempo_subtag(self, fn, expected):
        assert self.e0 is not None
        result = to_float(get_tempo_subtag(fn, self.e0))
        assert result == expected


    def test_traktor_get_location(self):
        assert self.e0 is not None
        result = get_location(self.e0)
        assert result.as_posix() == path_anchor(None).as_posix() + 'Users/myname/Music/David Guetta/Beautiful People - Single/David_Guetta,_Sia_-_Beautiful_People_(Extended).mp3'


    @pytest.mark.parametrize("anchor, rel, expected", [
        (Path(path_anchor(None)).joinpath('mnt'), Path(path_anchor(None)).joinpath('Users', 'myname'), Path(path_anchor(None)).joinpath('mnt', 'Music', 'David Guetta', 'Beautiful People - Single/David_Guetta,_Sia_-_Beautiful_People_(Extended).mp3')),
        (None, None, Path(path_anchor(None)).joinpath('Users', 'myname', 'Music', 'David Guetta', 'Beautiful People - Single/David_Guetta,_Sia_-_Beautiful_People_(Extended).mp3')),
        (Path(path_anchor(None)).joinpath('mnt'), None, Path(path_anchor(None)).joinpath('mnt', 'Users', 'myname', 'Music', 'David Guetta', 'Beautiful People - Single/David_Guetta,_Sia_-_Beautiful_People_(Extended).mp3')),
        (None, Path(path_anchor(None)).joinpath('Users', 'myname'), Path(path_anchor(None)).joinpath('Music', 'David Guetta', 'Beautiful People - Single/David_Guetta,_Sia_-_Beautiful_People_(Extended).mp3')),
    ])
    def test_traktor_adjust_location(self, anchor, rel, expected):
        assert self.e0 is not None
        result = adjust_location(get_location(self.e0), anchor, rel)
        assert result.as_posix() == expected.as_posix()


    def test_traktor_get_loudness(self):
        assert self.e0 is not None
        result = get_loudness(self.e0)
        assert result == ALoudness(0.0, 0.0)


    def test_traktor_get_musical_key_subtag(self):
        assert self.e0 is not None
        result = get_musical_key_subtag('tonality', self.e0)
        assert result == '21'
        assert musical_key_to_classic_key(result) == 'Fmin'


    def test_traktor_get_beatgrid(self):
        assert self.e0 is not None
        result = get_cue_v2_beatgrid(self.e0)
        assert result == [ABeatGridBPM(position=0.052261284000000005,
                                      bpm=126.999878,
                                      metro=(4, 4))
                          ]


    def test_traktor_get_cues(self):
        assert self.e0 is not None
        result = get_cue_v2_cues(self.e0)
        assert result == [AMarker(name='n.n.',
                                  color=None,
                                  start=0.052261284000000005,
                                  end=None,
                                  kind=AMarkerType.CUE,
                                  index=0,
                                  locked=False),
                          AMarker(name='n.n.',
                                  color=None,
                                  start=30.288510819,
                                  end=34.068042010999996,
                                  kind=AMarkerType.LOOP,
                                  index=1,
                                  locked=False),
                          ]


    def test_traktor_read_playlist(self):
        assert self.e0 is not None
        result = read_traktor_playlist(self.nml_path, None, self.trans)
        assert result.entries == 2
        assert result.name == 'test'
        assert list(map(lambda at: at.title, result.tracks)) == [
            'Beautiful People (Extended)',
            'You Used To Salsa'
        ]
