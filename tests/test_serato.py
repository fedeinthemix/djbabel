from datetime import date
import datetime
import mutagen
from pathlib import Path, PurePosixPath, PureWindowsPath
import pytest

from djbabel.types import (
    ABeatGridBPM,
    ADataSource,
    AFormat,
    ALoudness,
    AMarker,
    APlaylist,
    ASoftware,
    ASoftwareInfo,
    ATrack,
    ATransformation,
    AMarkerType,
    AMarkerColors,
    AEncoder,
    AEncoderMode
)

from djbabel.utils import to_float

from djbabel.serato.markers2 import (
    CueEntry,
    get_serato_markers_v2,
    ColorEntry,
    BpmLockEntry,
    LoopEntry
)

from djbabel.serato.utils import (
    serato_metadata,
    maybe_metadata,
    serato_tag_name
)

from djbabel.serato.types import SeratoTags

from djbabel.serato.read import (
    std_tag_text,
    track_number,
    release_date,
    location,
    audio_file_type,
    beatgrid,
    get_markers,
    locked,
    average_bpm,
    loudness,
    data_source,
    get_serato_markers_v2,
    from_serato,
    read_serato_playlist
)

from djbabel.serato.write import (
    to_serato_analysis,
    to_serato_autotags,
    to_serato_beatgrid,
    to_serato_markers_v2,
    to_serato_markers,
    dump_serato_analysis,
    dump_serato_autotags,
    dump_serato_beatgrid,
    dump_serato_markers_v2,
    add_envelope,
    dump_serato_markers,
    to_serato_playlist,
)

###############################################################
# Read files

class TestSeratoReadTags:

    trans = ATransformation(ASoftwareInfo(ASoftware.SERATO_DJ_PRO, (3,2,4)),
                            ASoftwareInfo(ASoftware.REKORDBOX, (7,1,3)))

    file_mp3 = Path("tests") / "audio" / "test_audio_1.mp3"
    file_flac = Path("tests") / "audio" / "test_audio_1.flac"
    file_m4a = Path("tests") / "audio" / "test_audio_1.m4a"

    audio_mp3 = mutagen.File(file_mp3, easy=False)
    audio_flac = mutagen.File(file_flac, easy=False)
    audio_m4a = mutagen.File(file_m4a, easy=False)


    @pytest.mark.parametrize("fn, audio, expected", [
        ('title', audio_mp3, 'Weekend (Original Mix)'),
        ('title', audio_m4a, 'Go'),
        ('title', audio_flac, 'Pump Up The Volume'),
    ])
    def test_serato_std_tag_text(self, fn, audio, expected):
        result = std_tag_text(fn, audio)
        assert result == expected


    @pytest.mark.parametrize("fn, audio, expected", [
        ('track_number', audio_mp3, 2),
        ('track_number', audio_m4a, None),
        ('track_number', audio_flac, None),
    ])
    def test_serato_track_number(self, fn, audio, expected):
        result = track_number(std_tag_text(fn, audio))
        assert result == expected


    @pytest.mark.parametrize("audio, expected", [
        (audio_mp3, date(1988, 8, 9)),
        (audio_m4a, date(1988, 1, 1)),
        (audio_flac, date(1987, 1, 1)),
    ])
    def test_serato_release_date(self, audio, expected):
        result = release_date(audio)
        assert result == expected


    @pytest.mark.parametrize("audio, expected", [
        (audio_mp3, file_mp3),
        (audio_m4a, file_m4a),
        (audio_flac, file_flac),
    ])
    def test_serato_location(self, audio, expected):
        result = location(audio)
        assert result == expected


    @pytest.mark.parametrize("audio, expected", [
        (audio_mp3, AFormat.MP3),
        (audio_m4a, AFormat.M4A),
        (audio_flac, AFormat.FLAC),
    ])
    def test_serato_audio_file_type(self, audio, expected):
        result = audio_file_type(audio)
        assert result == expected


    @pytest.mark.parametrize("audio, expected", [
        (audio_mp3, [ABeatGridBPM(position=5.803330421447754,
                                  bpm=122.81898268224539,
                                  metro=(4, 4)),
                     ABeatGridBPM(position=154.3145751953125,
                                  bpm=122.9070816040039,
                                  metro=(4, 4))]),
        (audio_m4a, [ABeatGridBPM(position=1.5416836738586426,
                                  bpm=113.68891143798828,
                                  metro=(4, 4))]),
        (audio_flac, [ABeatGridBPM(position=0.5390172600746155,
                                   bpm=112.5244137525537,
                                   metro=(4, 4)),
                      ABeatGridBPM(position=171.1686553955078,
                                   bpm=107.47166923468498,
                                   metro=(4, 4)),
                      ABeatGridBPM(position=175.63494873046875,
                                   bpm=107.87559969410886,
                                   metro=(4, 4)),
                      ABeatGridBPM(position=180.0845184326172,
                                   bpm=113.63721091531743,
                                   metro=(4, 4)),
                      ABeatGridBPM(position=184.30848693847656,
                                   bpm=112.48766989559304,
                                   metro=(4, 4)),
                      ABeatGridBPM(position=235.51409912109375,
                                   bpm=112.48429107666016,
                                   metro=(4, 4))]),
    ])
    def test_serato_beatgrid(self, audio, expected):
        result = beatgrid(audio)
        assert result == expected


    @pytest.mark.parametrize("audio, expected", [
        (audio_mp3, [AMarker(name='intro', color=AMarkerColors.MAGENTA,
                             start=0.25,
                             end=None,
                             kind=AMarkerType.CUE,
                             index=0,
                             locked=False),
                     AMarker(name='16', color=AMarkerColors.BRIGHT_GREEN,
                             start=5.81,
                             end=None,
                             kind=AMarkerType.CUE,
                             index=1,
                             locked=False),
                     AMarker(name='tonoght the night',
                             color=AMarkerColors.ORANGE,
                             start=154.314,
                             end=None,
                             kind=AMarkerType.CUE,
                             index=2,
                             locked=False),
                     AMarker(name='3 x 32',
                             color=AMarkerColors.RED,
                             start=185.557,
                             end=None,
                             kind=AMarkerType.CUE,
                             index=3,
                             locked=False),
                     AMarker(name='',
                             color=AMarkerColors.SKY_BLUE,
                             start=201.165,
                             end=216.791,
                             kind=AMarkerType.LOOP,
                             index=0,
                             locked=False)]),
        (audio_m4a, [AMarker(name='16',
                             color=AMarkerColors.LIME_gREEN,
                             start=1.541,
                             end=None,
                             kind=AMarkerType.CUE,
                             index=0,
                             locked=False),
                     AMarker(name='tromba',
                             color=AMarkerColors.DARK_BLUE,
                             start=9.691,
                             end=None,
                             kind=AMarkerType.CUE,
                             index=1,
                             locked=False),
                     AMarker(name='32',
                             color=AMarkerColors.RED,
                             start=94.417,
                             end=None,
                             kind=AMarkerType.CUE,
                             index=2,
                             locked=False),
                     AMarker(name='28',
                             color=AMarkerColors.RED,
                             start=174.636,
                             end=None,
                             kind=AMarkerType.CUE,
                             index=3,
                             locked=False),
                     AMarker(name='',
                             color=AMarkerColors.SKY_BLUE,
                             start=98.645,
                             end=107.089,
                             kind=AMarkerType.LOOP,
                             index=0,
                             locked=True),
                     AMarker(name='',
                             color=AMarkerColors.SKY_BLUE,
                             start=178.857,
                             end=187.301,
                             kind=AMarkerType.LOOP,
                             index=1,
                             locked=True)]),
        (audio_flac, [AMarker(name='',
                              color=AMarkerColors.LIME_gREEN,
                              start=0.534,
                              end=None,
                              kind=AMarkerType.CUE,
                              index=0,
                              locked=False),
                      AMarker(name='pump',
                              color=AMarkerColors.ORANGE,
                              start=180.078,
                              end=None,
                              kind=AMarkerType.CUE,
                              index=1,
                              locked=False),
                      AMarker(name='dance',
                              color=AMarkerColors.MAGENTA,
                              start=183.252,
                              end=None,
                              kind=AMarkerType.CUE,
                              index=2,
                              locked=False),
                      AMarker(name='bass line',
                              color=AMarkerColors.DARK_BLUE,
                              start=184.308,
                              end=None,
                              kind=AMarkerType.CUE,
                              index=3,
                              locked=False),
                      AMarker(name='32',
                              color=AMarkerColors.RED,
                              start=235.514,
                              end=None,
                              kind=AMarkerType.CUE,
                              index=4,
                              locked=False),
                      AMarker(name='',
                              color=AMarkerColors.SKY_BLUE,
                              start=184.308,
                              end=192.842,
                              kind=AMarkerType.LOOP,
                              index=0,
                              locked=True)]),
    ])
    def test_serato_get_markers(self, audio, expected):
        result = get_markers(get_serato_markers_v2(audio))
        assert result == expected


    @pytest.mark.parametrize("audio, expected", [
        (audio_mp3, ALoudness(autogain=-2.213, gain_db=0.0)),
        (audio_m4a, ALoudness(autogain=7.519, gain_db=0.0)),
        (audio_flac, ALoudness(autogain=8.121, gain_db=0.0)),
    ])
    def test_serato_loudness(self, audio, expected):
        result = loudness(audio)
        assert result == expected


    @pytest.mark.parametrize("audio, expected", [
        (audio_mp3, ADataSource(software=ASoftware.SERATO_DJ_PRO,
                                version=[2, 1],
                                encoder=AEncoder(text='LAME 3.100.0+',
                                                 settings='-V 2',
                                                 mode=AEncoderMode.VBR))),
        (audio_m4a, ADataSource(software=ASoftware.SERATO_DJ_PRO,
                                version=[0, 1, 0],
                                encoder=None)),
        (audio_flac, ADataSource(software=ASoftware.SERATO_DJ_PRO,
                                 version=[0, 1, 0],
                                 encoder=None)),
    ])
    def test_serato_data_source(self, audio, expected):
        result = data_source(audio)
        assert result == expected

###############################################################
# Write files

class TestSeratoWriteTags:

    trans = ATransformation(ASoftwareInfo(ASoftware.SERATO_DJ_PRO, (3,2,4)),
                            ASoftwareInfo(ASoftware.SERATO_DJ_PRO, (3,2,4)))

    file_mp3 = Path("tests") / "audio" / "test_audio_1.mp3"
    file_flac = Path("tests") / "audio" / "test_audio_1.flac"
    file_m4a = Path("tests") / "audio" / "test_audio_1.m4a"

    audio_mp3 = mutagen.File(file_mp3, easy=False)
    audio_flac = mutagen.File(file_flac, easy=False)
    audio_m4a = mutagen.File(file_m4a, easy=False)

    @pytest.mark.parametrize("audio, stag, fn", [
        #### analysis ####
        (audio_mp3, SeratoTags.ANALYSIS,
         lambda x, s: dump_serato_analysis(to_serato_analysis(x))),
        (audio_m4a, SeratoTags.ANALYSIS,
         lambda x, s: add_envelope(dump_serato_analysis(to_serato_analysis(x)), s)),
        (audio_flac, SeratoTags.ANALYSIS,
         lambda x, s: add_envelope(dump_serato_analysis(to_serato_analysis(x)), s)),
        #### autotags ####
        (audio_mp3, SeratoTags.AUTOTAGS,
         lambda x, s: dump_serato_autotags(to_serato_autotags(x))),
        (audio_m4a, SeratoTags.AUTOTAGS,
         lambda x, s: add_envelope(dump_serato_autotags(to_serato_autotags(x)), s)),
        (audio_flac, SeratoTags.AUTOTAGS,
         lambda x, s: add_envelope(dump_serato_autotags(to_serato_autotags(x)), s)),
        #### beatgrids ####
        ## Footnote seems random, but we set it to 0.
        ## Hence we can only test files with a Footer value of '.
        # (audio_mp3, SeratoTags.BEATGRID,
        #  lambda x, s: dump_serato_beatgrid(to_serato_beatgrid(x))),
        # (audio_m4a, SeratoTags.BEATGRID,
        #  lambda x, s: add_envelope(dump_serato_beatgrid(to_serato_beatgrid(x)), s)),
        (audio_flac, SeratoTags.BEATGRID,
         lambda x, s: add_envelope(dump_serato_beatgrid(to_serato_beatgrid(x)), s)),
        #### markers2 ####
        (audio_mp3, SeratoTags.MARKERS2,
         lambda x, s: dump_serato_markers_v2(to_serato_markers_v2(x))),
        (audio_m4a, SeratoTags.MARKERS2,
         lambda x, s: add_envelope(dump_serato_markers_v2(to_serato_markers_v2(x)), s)),
        (audio_flac, SeratoTags.MARKERS2,
         lambda x, s: add_envelope(dump_serato_markers_v2(to_serato_markers_v2(x)), s)),
        #### markers ####
        (audio_mp3, SeratoTags.MARKERS,
         lambda x, s: dump_serato_markers(to_serato_markers(x), AFormat.MP3)),
        (audio_m4a, SeratoTags.MARKERS,
         lambda x, s: add_envelope(dump_serato_markers(to_serato_markers(x), AFormat.M4A), s)),
        (audio_flac, SeratoTags.MARKERS,
         lambda x, s: to_serato_markers(x)),
    ])
    def test_serato_analysis(self, audio, stag, fn):
        at = from_serato(audio)
        ty = audio_file_type(audio)
        expected = maybe_metadata(audio, serato_tag_name(stag, ty))
        result = fn(at, stag)
        if result == []: # FLAC doesn't use MARKERS
            result = None
        assert result == expected

###############################################################
# Crates

class TestSeratoCrate:
    trans = ATransformation(ASoftwareInfo(ASoftware.SERATO_DJ_PRO, (3,2,4)),
                            ASoftwareInfo(ASoftware.SERATO_DJ_PRO, (3,2,4)))

    file_mp3 = Path("tests") / "audio" / "crate_write_test.mp3"
    file_flac = Path("tests") / "audio" / "crate_write_test.flac"
    file_m4a = Path("tests") / "audio" / "crate_write_test.m4a"

    file_mp3_ref = Path("tests") / "audio" / "crate_write_test_ref.mp3"
    file_flac_ref = Path("tests") / "audio" / "crate_write_test_ref.flac"
    file_m4a_ref = Path("tests") / "audio" / "crate_write_test_ref.m4a"

    audio_mp3_ref = mutagen.File(file_mp3_ref, easy=False) # pyright: ignore
    audio_flac_ref = mutagen.File(file_flac_ref, easy=False) # pyright: ignore
    audio_m4a_ref = mutagen.File(file_m4a_ref, easy=False) # pyright: ignore

    def clear_tags(self, path: Path):
        a = mutagen.File(path, easy=False)  # pyright: ignore
        a.delete()                          # pyright: ignore
        a.save()                            # pyright: ignore


    def test_serato_playlist(self):
        crate = Path("tests") / 'subcrates' / 'crate_write_test.crate'

        # clear tags of files that we write.
        for a in [self.file_mp3, self.file_flac, self.file_m4a]:
            self.clear_tags(a)

        # Change 'at.location' to preserve the reference files.
        at_mp3 = from_serato(self.audio_mp3_ref) # pyright: ignore
        at_mp3.location = self.file_mp3
        at_flac = from_serato(self.audio_flac_ref) # pyright: ignore
        at_flac.location = self.file_flac
        at_m4a = from_serato(self.audio_m4a_ref) # pyright: ignore
        at_m4a.location = self.file_m4a

        apl_ref = APlaylist('crate_write_test', [at_mp3, at_flac, at_m4a])
        to_serato_playlist(apl_ref, crate, self.trans)
        apl = read_serato_playlist(crate, self.trans, anchor=Path(""))

        assert apl == apl_ref
