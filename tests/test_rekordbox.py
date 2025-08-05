from datetime import date
from pathlib import Path, PureWindowsPath
import pytest

from djbabel.rekordbox.write import rb_attr_color, rb_attr_location, rb_attr_rating, rb_attr_tonality, rb_battito, rb_marker_color, rb_position_mark, to_rekordbox
from djbabel.types import AMarker, AMarkerColors, ASoftwareInfo, ASoftware, ATransformation, AMarkerType, ABeatGridBPM

###############################################################

class TestRekordbox:

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
