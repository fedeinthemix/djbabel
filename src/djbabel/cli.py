# Run as
# python -m djbabel.cli -f sdjpro3 playlist.crate

import argparse
from pathlib import Path
from mutagen import MutagenError # pyright: ignore
import warnings

from .types import APlaylist, ASoftware, ADataSource
from .serato import read_serato_playlist
from .rekordbox import to_rekordbox_playlist

#######################################################################
# Warnings

def custom_formatwarning(message, _category, _filename, _lineno, _file=None, _line=None) -> str:
    """
    A custom formatwarning function that only returns the warning message.
    """
    return f"Warning: {message}\n"

# Apply the custom formatter
warnings.formatwarning = custom_formatwarning

#######################################################################
# Helpers

def parse_input_format(arg: str) -> ADataSource:
    match arg:
        case 'sdjpro':
            return ADataSource(ASoftware.SERATO_DJ_PRO, [3,3,2])
        case _:
            raise ValueError(f'Input format {arg} not supported')


def parse_output_format(arg: str) -> ADataSource:
    match arg:
        case 'rb6':
            # The version defined here is written in the XLM file.
            # Use a released version compatible with the RB6 format.
            return ADataSource(ASoftware.REKORDBOX, [7,1,3])
        case _:
            raise ValueError(f'Output format {arg} not supported')


def get_playlist(filepath: Path, source: ADataSource, anchor: Path | None, relative: Path | None) -> APlaylist:
    match source:
        case ADataSource(ASoftware.SERATO_DJ_PRO, _):
            return read_serato_playlist(filepath, anchor, relative)
        case _:
            raise ValueError(f'Source format {source} not supported.')


def create_playlist(playlist: APlaylist, filepath: Path, target: ADataSource) -> None:
    match target:
        case ADataSource(ASoftware.REKORDBOX, ver):
            return to_rekordbox_playlist(playlist, filepath, '.'.join(map(str,ver)))
        case _:
            raise ValueError(f'Target format {target} not supported.')


def output_filename(ofile: Path | None, ifile: Path, target: ADataSource) -> Path:
    if ofile is None:
        match target.software:
            case ASoftware.REKORDBOX:
                ofile = Path(ifile.stem + '.xml')
            case ASoftware.SERATO_DJ_PRO:
                ofile = Path(ifile.stem + '.crate')
    if ofile.exists():
        overwrite = input(f'file {ofile} exists. Overwrite (y/[n])? ')
        if overwrite.lower() != 'y':
            raise ValueError(f'Please choose another target playlist file name.')
    return ofile
    
#######################################################################
# Main

def main():
    desc = """DJ Software playlists convertion tool.

    djbabel converts playlists between various DJ programs, currently
    Serato DJ Pro and Rekordbox. Some playlist formats, such as Crates
    in Serato DJ Pro, store file path without the anchor (the
    concatenation of the drive and root). In this case, djbabel
    assumes 'C:\\' on Windows and '/' on POSIX systems. If this is not
    correct, you have to specify it with the '--anchor' option.

    The option '--relative' can be used to strip part of the leading
    path of the audio file paths in the playlist. For example, if you
    created a Serato Crate on Windows, then copied your 'Music' folder
    to an external harddrive directory called 'backup' on drive 'D',
    you can access the files using

    $ djbabel -r 'Users\\name' -a 'D:\\' playlist.crate

    Note however that the path sotred in the generated netlist is the
    new one, not the original.

    """
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("ifile", type=Path,
                        help="input playlist path")
    parser.add_argument('-s', '--source', type=str, choices=['sdjpro'],
                        default='sdjpro',
                        help='source playlist format')
    parser.add_argument('-t', '--target', type=str, choices=['rb6'],
                        default='rb6',
                        help='target playlist format')
    parser.add_argument('-o', '--ofile', type=Path,
                        help='output file name')
    parser.add_argument('-a', '--anchor', type=Path,
                        help='anchor for tracks in a playlist')
    parser.add_argument('-r', '--relative', type=Path,
                        help='make track paths in a playlist relative to this argument')

    args = parser.parse_args()
    # print(args)

    try:
        source = parse_input_format(args.source)
        target = parse_output_format(args.target)
        ofile = output_filename(args.ofile, args.ifile, target)
        playlist = get_playlist(args.ifile, source, args.anchor, args.relative)
        # print(playlist)
        create_playlist(playlist, ofile, target)
    except ValueError as err:
        print(f'{err}')
    except MutagenError as err:
        print(f'Playlist track error: {err}')
    except OSError as err:
        print('OS error:', err)
    except Exception as err:
        print(f'Unexpected error: {err}')

if __name__ == "__main__":
    main()
