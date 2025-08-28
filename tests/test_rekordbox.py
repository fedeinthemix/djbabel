# SPDX-FileCopyrightText: NONE
#
# SPDX-License-Identifier: CC0-1.0

from datetime import date
from pathlib import Path, PureWindowsPath
import pytest
import xml.etree.ElementTree as ET

from djbabel.rekordbox.write import (
    rb_attr_color,
    rb_attr_location,
    rb_attr_rating,
    rb_attr_tonality,
    rb_battito,
    rb_marker_color,
    rb_position_mark,
    to_rekordbox
)

from djbabel.rekordbox.types import RBPlaylistKeyType

from djbabel.rekordbox.read import(
    find_collection_entry,
    get_tag_attr,
    get_tonality,
    file_size,
    audio_length,
    get_beatgrid,
    get_markers,
    get_color,
    get_playlist_key_type,
    get_rb_location,
    read_rekordbox_playlist
)

from djbabel.types import (
    AMarker,
    AMarkerColors,
    ASoftwareInfo,
    ASoftware,
    ATransformation,
    AMarkerType,
    ABeatGridBPM
)

from djbabel.utils import (
    path_anchor,
)

###############################################################

class TestRekordboxWriteTags:

    trans = ATransformation(ASoftwareInfo(ASoftware.SERATO_DJ_PRO, (3,2,3)),
                            ASoftwareInfo(ASoftware.REKORDBOX, (7,1,3)))


    @pytest.mark.parametrize("path, expected", [
        (Path('/tmp') / 'test.flac', 'file://localhost/tmp/test.flac'),
        (PureWindowsPath('C:\\tmp') / 'beautiful_poples.mp3', 'file://localhost/C%3A/tmp/beautiful_poples.mp3'),
    ])
    def test_rb_attr_location(self, path, expected):
        result = rb_attr_location(path)
        assert result == expected


    @pytest.mark.parametrize("t, expected", [
        ('Bmaj', 'B'),
    ])
    def test_rb_attr_tonality(self, t, expected):
        result = rb_attr_tonality(t)
        assert result == expected


    @pytest.mark.parametrize("r", [0, 51, 102, 153, 204, 255,])
    def test_rb_attr_rating(self, r):
        expected = str(r)
        result = rb_attr_rating(r)
        assert result == expected


    @pytest.mark.parametrize("c, s, expected", [
        ((255, 0, 0), ASoftware.SERATO_DJ_PRO, '0xFFFF00'), # not from RB -> default (Lemon)
        ((255, 165, 0), ASoftware.REKORDBOX, '0xFFA500'), # Orange from RB
    ])
    def test_rb_attr_color(self, c, s, expected):
        result = rb_attr_color(c, s)
        assert result == expected


    @pytest.mark.parametrize("c, expected", [
        (AMarkerColors.RED, (230, 40, 40)), # reddiest in RB palette
        (AMarkerColors.DARK_GREEN, (40, 226, 20)), # greenest in RB palette
        (AMarkerColors.BLUE, (48, 90, 255)), # bluest in RB palette
    ])
    def test_rb_marker_color(self, c, expected):
        result = rb_marker_color(c)
        assert result == expected


    @pytest.mark.parametrize("bpms, idx, expected", [
        ([ABeatGridBPM(position=0.0, bpm=120.0, metro=(4, 4)),
          ABeatGridBPM(position=30.0, bpm=240.0, metro=(4, 4)),
          ABeatGridBPM(position=60.5, bpm=120.0, metro=(4, 4))], 0, 1),
        ([ABeatGridBPM(position=0.0, bpm=120.0, metro=(4, 4)),
          ABeatGridBPM(position=30.0, bpm=240.0, metro=(4, 4)),
          ABeatGridBPM(position=60.25, bpm=120.0, metro=(4, 4))], 1, 1),
        ([ABeatGridBPM(position=0.0, bpm=120.0, metro=(4, 4)),
          ABeatGridBPM(position=30.5, bpm=240.0, metro=(4, 4)),
          ABeatGridBPM(position=60.5, bpm=120.0, metro=(4, 4))], 1, 2),
        ([ABeatGridBPM(position=0.0, bpm=120.0, metro=(4, 4)),
          ABeatGridBPM(position=31.0, bpm=240.0, metro=(4, 4)),
          ABeatGridBPM(position=61.0, bpm=120.0, metro=(4, 4))], 1, 3),
        ([ABeatGridBPM(position=0.0, bpm=120.0, metro=(4, 4)),
          ABeatGridBPM(position=30.0, bpm=240.0, metro=(4, 4)),
          ABeatGridBPM(position=60.25, bpm=120.0, metro=(4, 4))], 2, 2),
        ([ABeatGridBPM(position=0.0, bpm=120.0, metro=(4, 4)),
          ABeatGridBPM(position=30.0, bpm=240.0, metro=(4, 4)),
          ABeatGridBPM(position=60.5, bpm=120.0, metro=(4, 4))], 2, 3),
    ])
    def test_rb_battito(self, bpms, idx, expected):
        result = rb_battito(bpms, idx)
        assert result == expected


    @pytest.mark.parametrize("m, expected", [
        (AMarker('name', AMarkerColors.RED, 1.0, None, AMarkerType.CUE, 3, False),
         {
             'Name': 'name',
             'Type': '0',
             'Start': '1.0',
             'End': '',
             'Num': '3',
             # closest to RED in RB palette
             'Red': '230',
             'Green': '40',
             'Blue': '40'
         }),
    ])
    def test_rb_position_marker(self, m, expected):
        result = rb_position_mark(m)
        assert result.attrib == expected


    def test_to_rekordbox(self, atrack_input_1):
        result = to_rekordbox(atrack_input_1, 0, self.trans)
        assert result.attrib == {'Name': 'title',
                                 'Artist': 'artist',
                                 'Composer': 'composer',
                                 'Album': 'album',
                                 'Grouping': 'grouping',
                                 'Genre': 'genre',
                                 'kind': 'FLAC File',
                                 'Size': '12345',
                                 'TotalTime': '1',
                                 'DiscNumber': '0',
                                 'TrackNumber': '2',
                                 'Year': '2025',
                                 'AverageBpm': '120.0',
                                 'DateAdded': '2025-01-02',
                                 'BitRate': '0',
                                 'SampleRate': '44100',
                                 'Comments': 'comments',
                                 'Rating': '255',
                                 'Location': 'file://localhost/tmp/test.flac',
                                 'Remixer': 'remixer',
                                 'Tonality': 'B',
                                 'Label': 'label',
                                 'Mix': 'mix',
                                 'Colour': '0xFFFF00',
                                 'TrackID': '1'}
        for m in result:
            match m.tag:
                case 'POSITION_MARK':
                    # Cues
                    assert result[0].attrib == {'Name': '32',
                                                'Type': '0',
                                                'Start': '1.0',
                                                'End': '',
                                                'Num': '0',
                                                'Red': '230',
                                                'Green': '40',
                                                'Blue': '40'}
                case 'TEMPO':
                    # Beatgrid
                    assert result[1].attrib == {'Inizio': '0.04',
                                                'Bpm': '120.4',
                                                'Metro': '4/4',
                                                'Battito': '1'}
                case _:
                    assert False

###############################################################
# Read XML files

class TestRekordboxReadTags:

    trans = ATransformation(ASoftwareInfo(ASoftware.REKORDBOX, (7,1,3)),
                            ASoftwareInfo(ASoftware.TRAKTOR, (4,2,0)))


    xml_path = Path('tests') / 'rb7xml' / 'rbxml_test.xml'
    root = ET.parse(xml_path).getroot()
    col = root.find('COLLECTION')
    assert col is not None
    pls = root.findall('.//NODE[@Type="1"]')
    pl = list(filter(lambda pl: pl.attrib['Name'] == 'rbxml_test', pls))[0]
    pl_keys = pl.findall('./TRACK')
    e0 = find_collection_entry(col, pl_keys[0].get('Key'), RBPlaylistKeyType.TRACK_ID)
    e1 = find_collection_entry(col, pl_keys[1].get('Key'), RBPlaylistKeyType.TRACK_ID)


    @pytest.mark.parametrize("fn, expected", [
        ('title', "Weekend (Original Mix)"),
        ('genre', "House"),
        ('not_defined', None),
        ('', None),
    ])
    def test_rekordbox_get_tag_attr(self, fn, expected):
        assert self.e0 is not None
        result = get_tag_attr(fn, self.e0)
        assert result == expected


    def test_rekordbox_get_tonality(self):
        assert self.e0 is not None
        result = get_tonality(self.e0)
        assert result == 'Bbmaj'


    def test_rekordbox_get_location(self):
        assert self.e0 is not None
        result = get_rb_location(self.e0)
        assert result.as_posix() == path_anchor(None).as_posix() + 'tests/audio/crate_write_test.mp3'


    def test_rekordbox_get_beatgrid(self):
        assert self.e0 is not None
        result = get_beatgrid(self.e0)
        assert result == [
            ABeatGridBPM(
                position=5.803330421447754,
                bpm=122.81898268224539,
                metro=(4,4),
            ),
            ABeatGridBPM(
                position=154.3145751953125,
                bpm=122.9070816040039,
                metro=(4,4),
            ),
        ]


    def test_rekordbox_get_markers(self):
        assert self.e0 is not None
        result = get_markers(self.e0)
        assert result == [
            AMarker(name='intro',
                    color=AMarkerColors.MAGENTA,
                    start=0.25,
                    end=None,
                    kind=AMarkerType.CUE,
                    index=0,
                    locked=False),
            AMarker(
                name='16',
                color=AMarkerColors.DARK_GREEN,
                start=5.81,
                end=None,
                kind=AMarkerType.CUE,
                index=1,
                locked=False,
            ),
            AMarker(
                name='tonoght the night',
                color=AMarkerColors.RED_ORANGE,
                start=154.314,
                end=None,
                kind=AMarkerType.CUE,
                index=2,
                locked=False,
            ),
            AMarker(
                name='3 x 32',
                color=AMarkerColors.RED,
                start=185.557,
                end=None,
                kind=AMarkerType.CUE,
                index=3,
                locked=False,
            ),
            AMarker(
                name='',
                color=AMarkerColors.SKY_BLUE,
                start=201.165,
                end=216.791,
                kind=AMarkerType.LOOP,
                index=7,
                locked=False,
            ),
        ]


    def test_rekordbox_read_playlist(self):
        assert self.e0 is not None
        result = read_rekordbox_playlist(self.xml_path, None, self.trans)
        assert result.entries == 3
        assert result.name == 'rbxml_test'
        assert list(map(lambda at: at.title, result.tracks)) == [
            'Weekend (Original Mix)',
            'Pump Up The Volume',
            'Go',
        ]
