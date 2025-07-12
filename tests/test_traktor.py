from datetime import date
from pathlib import Path, PureWindowsPath
import pytest

from djbabel.traktor.utils import traktor_path
from djbabel.traktor.write import info_tag, entry_tag, album_tag, modification_info_tag, tempo_tag, musical_key_tag, loudness_tag, location_tag, cue_v2_beatgrid, cue_v2_markers, to_traktor_playlist
from djbabel.types import ABeatGridBPM, ADataSource, AFormat, ALoudness, AMarker, ASoftware, ASoftwareInfo, ATrack, ATransformation, AMarkerType, AMarkerColors

###############################################################

@pytest.mark.parametrize("path, expected", [
    (Path('/tmp') / 'beautiful_poples.mp3', '/:tmp/:beautiful_poples.mp3'),
    (PureWindowsPath('C:\\tmp') / 'beautiful_poples.mp3', '/:tmp/:beautiful_poples.mp3'),
])
def test_traktor_path(path, expected):
    result = traktor_path(path)
    assert result == expected


class TestTraktorTags:
    # At the moment we don't test 'location_tag' and 'entry_tag' as
    # they need to access the Windows/macOS filesystem.
    
    trans = ATransformation(ASoftwareInfo(ASoftware.SERATO_DJ_PRO, (3,2,3)),
                            ASoftwareInfo(ASoftware.REKORDBOX, (7,1,3)))

    audio = ATrack(
        'title',
        'artist',
        'composer',
        'album',
        'grouping',
        'genre',
        AFormat.FLAC, # aformat
        0, # size
        1.0, # total_time
        0, # disc_number
        2, # track_number
        date(2025, 1, 1), # release_date 
        120.0, # average_bpm
        date(2025, 1, 2), # date_added
        320, # bit_rate
        44100, # sample_rate
        'comments',
        None, # play_count
        5, # rating
        Path('/tmp/test.flac'), # location
        'remixer',
        'Bmaj',
        'label',
        'mix',
        ADataSource(ASoftware.SERATO_DJ_PRO, [1,1,1]),
        [AMarker('32', AMarkerColors.RED, 1.0, None, AMarkerType.CUE, 0, False)], # markers
        [ABeatGridBPM(0.04, 120.4)], # beatgrid
        True, # locked
        (255, 255, 255), # color
        1, # trackID
        ALoudness(5.0, 0.0),
    )
    
    @pytest.mark.parametrize("audio, expected", [
        (audio, {'FLAGS': '9',
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
                 'LABEL': 'label'}),
    ])
    def test_traktor_info_tag(self, audio, expected):
        result = info_tag(audio, self.trans)
        assert result.attrib == expected


    @pytest.mark.parametrize("audio, expected", [
        (audio, {'ALBUM': 'album', 'DISC_NUMBER': '0', 'TRACK': '2'}),
    ])
    def test_traktor_album_tag(self, audio, expected):
        result = album_tag(audio, self.trans)
        assert result.attrib == expected


    @pytest.mark.parametrize("audio, expected", [
        (audio, {'AUTHOR_TYPE': 'user'}),
    ])
    def test_traktor_modification_info_tag(self, audio, expected):
        result = modification_info_tag(audio, self.trans)
        assert result.attrib == expected


    @pytest.mark.parametrize("audio, expected", [
        (audio, {'BPM_QUALITY': '100.000000', 'BPM': '120.0'}),
    ])
    def test_traktor_tempo_tag(self, audio, expected):
        result = tempo_tag(audio, self.trans)
        assert result.attrib == expected


    @pytest.mark.parametrize("audio, expected", [
        (audio, {'VALUE': '6d'}),
    ])
    def test_traktor_musical_key_tag(self, audio, expected):
        result = musical_key_tag(audio, self.trans)
        assert result.attrib == expected

    @pytest.mark.parametrize("audio, expected", [
        (audio, {'ANALYZED_DB': '5.0', 'PERCEIVED_DB': '5.0'}),
    ])
    def test_traktor_loudness_tag(self, audio, expected):
        result = loudness_tag(audio, self.trans)
        assert result.attrib == expected


    @pytest.mark.parametrize("audio, expected", [
        (audio, {'NAME': 'Beat Marker',
                 'TYPE': '4',
                 'START': '40.0',
                 'LEN': '0.0',
                 'HOTCUE': '-1',
                 'REPEATS': '-1',
                 'DISPL_ORDER': '0'}),
    ])
    def test_traktor_cue_v2_beatgrid_tag(self, audio, expected):
        result = cue_v2_beatgrid(audio.beatgrid[0])
        assert result.attrib == expected


    @pytest.mark.parametrize("audio, expected", [
        (audio, {'BPM': '120.4'}),
    ])
    def test_traktor_cue_v2_beatgrid_tag_grid(self, audio, expected):
        result = cue_v2_beatgrid(audio.beatgrid[0])
        assert result[0].attrib == expected
        assert result[0].tag == 'GRID'


    @pytest.mark.parametrize("audio, expected", [
        (audio, {'NAME': '32',
                 'TYPE': '0',
                 'START': '1000.0',
                 'LEN': '0.0',
                 'HOTCUE': '0',
                 'REPEATS': '-1',
                 'DISPL_ORDER': '0'}),
    ])
    def test_traktor_cue_v2_markers_tag(self, audio, expected):
        result = cue_v2_markers(audio.markers[0])
        assert result.attrib == expected
