import pytest
from datetime import date
from djbabel.types import ABeatGridBPM, ADataSource, AFormat, ALoudness, AMarker, ASoftware, ASoftwareInfo, ATrack, ATransformation, AMarkerType, AMarkerColors
from pathlib import Path

###############################################################

@pytest.fixture(scope="session")
def atrack_input_1():
    return ATrack(
        'title',
        'artist',
        'composer',
        'album',
        'grouping',
        'genre',
        AFormat.FLAC, # aformat
        12345, # size
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
        255, # rating
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
