# Run as
# python -m djbabel.cli -f sdjpro3 audio.mp3

import argparse
from pathlib import Path
from mutagen import MutagenError # pyright: ignore
import tempfile
import os
import warnings

from .types import APlaylist, ASoftware, ADataSource
from .serato import read_serato_playlist
from .rekordbox import to_rekordbox_playlist

#######################################################################
# Warnings

def custom_formatwarning(message, _category, _filename, _lineno, _file=None, _line=None):
    """
    A custom formatwarning function that only returns the warning message.
    """
    return f"Warning: {message}\n"

# Apply the custom formatter
warnings.formatwarning = custom_formatwarning

#######################################################################
# Helpers

def parse_input_format(arg) -> ADataSource:
    match arg:
        case 'sdjpro':
            return ADataSource(ASoftware.SERATO_DJ_PRO, [3])
        case _:
            raise ValueError(f'Input format {arg} not supported')


def parse_output_format(arg) -> ADataSource:
    match arg:
        case 'rb':
            return ADataSource(ASoftware.REKORDBOX, [7])
        case _:
            raise ValueError(f'Output format {arg} not supported')


def get_playlist(filepath: Path, source: ADataSource) -> APlaylist:
    match source:
        case ADataSource(ASoftware.SERATO_DJ_PRO, _):
            return read_serato_playlist(filepath)
        case _:
            raise ValueError(f'Source format {source} not supported.')


def create_playlist(playlist: APlaylist, filepath: Path, target: ADataSource) -> None:
    match target:
        case ADataSource(ASoftware.REKORDBOX, _):
            return to_rekordbox_playlist(playlist, filepath)
        case _:
            raise ValueError(f'Target format {target} not supported.')


def make_unique_if_exists(fn: Path) -> Path:
    if fn.exists():
        warnings.warn(f'File {fn} exists! Adding unique suffix.', stacklevel=0)
        ofd, ofn = tempfile.mkstemp(prefix=fn.stem, suffix=fn.suffix, dir=os.getcwd())
        ofile = Path(ofn)
        os.close(ofd)
        return ofile
    else:
        return fn


def output_filename(ofile: Path | None, ifile: Path, target: ADataSource) -> Path:
    if ofile is None:
        match target.software:
            case ASoftware.REKORDBOX:
                ofile = make_unique_if_exists(Path(ifile.stem + '.xml'))
            case ASoftware.SERATO_DJ_PRO:
                ofile = make_unique_if_exists(Path(ifile.stem + '.crate'))
        return ofile
    else:
        return ofile
    
    
#######################################################################
# Main

def main():
    parser = argparse.ArgumentParser(description="DJ Software playlists convertion tool.")
    parser.add_argument("ifile", type=Path,
                        help="input playlist path")
    parser.add_argument('-s', '--source', type=str, choices=['sdjpro'],
                        default='sdjpro',
                        help='source playlist format')
    parser.add_argument('-t', '--target', type=str, choices=['rb'],
                        default='rb',
                        help='target playlist format')
    parser.add_argument('-o', '--ofile', type=Path,
                        help='output file name')

    args = parser.parse_args()
    source = parse_input_format(args.source)
    target = parse_output_format(args.target)
    ofile = output_filename(args.ofile, args.ifile, target)
    
    # print(args)
    # print(ofile)

    try:
        playlist = get_playlist(args.ifile, source)
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
