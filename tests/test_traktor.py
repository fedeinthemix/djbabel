from datetime import date
from pathlib import Path, PureWindowsPath
import pytest

from djbabel.traktor.utils import traktor_path
from djbabel.traktor.write import info_tag, entry_tag, album_tag, modification_info_tag, tempo_tag, musical_key_tag, loudness_tag, location_tag, cue_v2_beatgrid, cue_v2_markers, to_traktor_playlist
from djbabel.types import ABeatGridBPM, ADataSource, AFormat, ALoudness, AMarker, ASoftware, ASoftwareInfo, ATrack, ATransformation, AMarkerType, AMarkerColors

###############################################################

class TestTraktorTags:
    # At the moment we don't test 'location_tag' and 'entry_tag' as
    # they need to access the Windows/macOS filesystem.
    
    trans = ATransformation(ASoftwareInfo(ASoftware.SERATO_DJ_PRO, (3,2,3)),
                            ASoftwareInfo(ASoftware.REKORDBOX, (7,1,3)))

    @pytest.mark.parametrize("path, expected", [
        (Path('/tmp') / 'beautiful_poples.mp3', '/:tmp/:beautiful_poples.mp3'),
        (PureWindowsPath('C:\\tmp') / 'beautiful_poples.mp3', '/:tmp/:beautiful_poples.mp3'),
    ])
    def test_traktor_path(self, path, expected):
        result = traktor_path(path)
        assert result == expected


    def test_traktor_info_tag(self, atrack_input_1):
        result = info_tag(atrack_input_1, self.trans)
        assert result.attrib == {'FLAGS': '9',
                                 'COMPOSER': 'composer',
                                 'GENRE': 'genre',
                                 'FILESIZE': '0',
                                 'PLAYTIME': '1',
                                 'PLAYTIME_FLOAT': '1.0',
                                 'RELEASE_DATE': '2025/01/01',
                                 'IMPORT_DATE': '2025/01/02',
                                 'BITRATE': '320',
                                 'COMMENT': 'comments',
                                 'PLAYCOUNT': '0',
                                 'RATING': '5',
                                 'REMIXER': 'remixer',
                                 'KEY': 'Bmaj',
                                'LABEL': 'label'}


    def test_traktor_album_tag(self, atrack_input_1):
        result = album_tag(atrack_input_1, self.trans)
        assert result.attrib == {'ALBUM': 'album', 'DISC_NUMBER': '0', 'TRACK': '2'}


    def test_traktor_modification_info_tag(self, atrack_input_1):
        result = modification_info_tag(atrack_input_1, self.trans)
        assert result.attrib == {'AUTHOR_TYPE': 'user'}


    def test_traktor_tempo_tag(self, atrack_input_1):
        result = tempo_tag(atrack_input_1, self.trans)
        assert result.attrib == {'BPM_QUALITY': '100.000000', 'BPM': '120.0'}


    def test_traktor_musical_key_tag(self, atrack_input_1):
        result = musical_key_tag(atrack_input_1, self.trans)
        assert result.attrib == {'VALUE': '6d'}

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
