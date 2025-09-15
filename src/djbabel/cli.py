# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
from mutagen import MutagenError # pyright: ignore
from pathlib import Path
import re
import sys
import warnings

from djbabel.version import __version__

from djbabel.types import (
    AudioFileInaccessibleWarning,
    ASoftwareInfo,
    APlaylist,
    ASoftware,
    ATransformation
)

from djbabel.serato import (
    read_serato_playlist,
    to_serato_playlist
)

from djbabel.rekordbox import (
    to_rekordbox_playlist,
    read_rekordbox_playlist
)

from djbabel.traktor import (
    to_traktor_playlist,
    read_traktor_playlist
)

#######################################################################
# Warnings

seen_warnings = set()

def custom_showwarning(message, category, filename, lineno, file=None, line=None):
    pattern = re.compile(r"File.*", re.DOTALL)
    output_file = file if file is not None else sys.stderr
    if pattern.match(str(message)) and category is AudioFileInaccessibleWarning:
        if category in seen_warnings:
            return  # Already seen, so we return without showing the warning
        seen_warnings.add(category)
        print(f"Warning: {message}\n", file=output_file)
    else:
        print(f"Warning: {message}\n", file=output_file)

# Apply the custom formatter
warnings.showwarning = custom_showwarning

#######################################################################
# Helpers

def parse_input_format(arg: str) -> ASoftwareInfo:
    match arg:
        case 'sdjpro':
            return ASoftwareInfo(ASoftware.SERATO_DJ_PRO, (3,3,2))
        case 'traktor4':
            return ASoftwareInfo(ASoftware.TRAKTOR, (4,2,0))
        case 'rb7':
            return ASoftwareInfo(ASoftware.REKORDBOX, (7,1,3))
        case _:
            raise ValueError(f'Input format {arg} not supported')


def parse_output_format(arg: str) -> ASoftwareInfo:
    match arg:
        case 'rb7':
            # The version defined here is written in the XLM file.
            # Use a released version compatible with the RB7 format.
            return ASoftwareInfo(ASoftware.REKORDBOX, (7,1,3))
        case 'traktor4':
            return ASoftwareInfo(ASoftware.TRAKTOR, (4,2,0))
        case 'sdjpro':
            return ASoftwareInfo(ASoftware.SERATO_DJ_PRO, (3,3,2))
        case _:
            raise ValueError(f'Output format {arg} not supported')


def get_playlist(filepath: Path, trans: ATransformation, name: str | None, anchor: Path | None, relative: Path | None) -> APlaylist:
    match trans.source:
        case ASoftwareInfo(ASoftware.SERATO_DJ_PRO, _):
            return read_serato_playlist(filepath, trans, anchor, relative)
        case ASoftwareInfo(ASoftware.TRAKTOR, (4, _, _)):
            return read_traktor_playlist(filepath, name, trans, anchor, relative)
        case ASoftwareInfo(ASoftware.REKORDBOX, (7, _, _)):
            return read_rekordbox_playlist(filepath, name, trans, anchor, relative)
        case _:
            raise ValueError(f'Source format {trans.source} not supported.')


def create_playlist(playlist: APlaylist, filepath: Path, trans: ATransformation, overwrite_tags: str) -> None:
    match trans.target:
        case ASoftwareInfo(ASoftware.REKORDBOX, _):
            return to_rekordbox_playlist(playlist, filepath, trans)
        case ASoftwareInfo(ASoftware.TRAKTOR, _):
            return to_traktor_playlist(playlist, filepath, trans)
        case ASoftwareInfo(ASoftware.SERATO_DJ_PRO, _):
            return to_serato_playlist(playlist, filepath, trans, overwrite_tags)
        case _:
            raise ValueError(f'Target format {trans.target} not supported.')


def output_filename(ofile: Path | None, ifile: Path, trans: ATransformation) -> Path:
    if ofile is None:
        match trans.target.software:
            case ASoftware.REKORDBOX:
                ofile = Path(ifile.stem + '.xml')
            case ASoftware.SERATO_DJ_PRO:
                ofile = Path(ifile.stem + '.crate')
            case ASoftware.TRAKTOR:
                ofile = Path(ifile.stem + '.nml')
    if ofile.exists():
        overwrite = input(f'file {ofile} exists. Overwrite (y/[n])? ')
        if overwrite.lower() != 'y':
            raise ValueError(f'Please choose another target playlist file name.')
    return ofile


#######################################################################
# Main

def main():
    desc = """DJ software playlists convertion tool.

    djbabel converts playlists between various DJ programs. Some
    playlist formats, such as Crates in Serato DJ Pro, store file path
    without the anchor (the concatenation of the drive and root). In
    this case, djbabel assumes 'C:\\' on Windows and '/' on POSIX
    systems. If this is not correct, you have to specify it with the
    '--anchor' option.

    The option '--relative' can be used to strip part of the leading
    path of the audio file paths in the playlist. For example, if you
    created a Serato Crate on Windows, then copied your 'Music' folder
    to an external harddrive directory called 'party' on drive 'D',
    you can access the files using

    $ djbabel -r 'Users\\name' -a 'D:\\party' playlist.crate

    Note: The path sotred in the generated netlist is the new one, not
    the original.

    """
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("ifile", type=Path,
                        help="input playlist path")
    parser.add_argument('-s', '--source', type=str, choices=['rb7', 'sdjpro', 'traktor4'],
                        default='sdjpro',
                        help='source playlist format')
    parser.add_argument('-t', '--target', type=str, choices=['rb7', 'traktor4', 'sdjpro'],
                        default='rb7',
                        help='target playlist format')
    parser.add_argument('-o', '--ofile', type=Path,
                        help='output file name')
    parser.add_argument('-a', '--anchor', type=Path,
                        help='anchor for tracks in a playlist')
    parser.add_argument('-r', '--relative', type=Path,
                        help='make track paths in a playlist relative to this argument')
    parser.add_argument('-n', '--playlist-name', type=str, default = '',
                        help='Specify the name of the playlist (if different from the file name)')
    parser.add_argument('-w', '--overwrite-tags',
                        action='store_const', const='Y', default='n',
                        help="Overwrite the audio file metadata standard tags (title, ...). By default, only DJ software specific tags are overwritten. Use with 'Serato DJ Pro' as target ('sdjpro'))")
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')

    args = parser.parse_args()

    try:
        trans = ATransformation(source = parse_input_format(args.source),
                                target = parse_output_format(args.target))
        ifile = args.ifile
        ofile = output_filename(args.ofile, args.ifile, trans)
        name = args.playlist_name if args.playlist_name != '' else None

        playlist = get_playlist(ifile, trans, name, args.anchor, args.relative)
        create_playlist(playlist, ofile, trans, args.overwrite_tags)
    except ValueError as err:
        print(f'{err}')
    except MutagenError as err:
        print(f'djbabel: Playlist track error: {err}')
    except OSError as err:
        print('djbabel: OS error:', err)
    except Exception as err:
        print(f'djbabel: Unexpected error: {err}')

if __name__ == "__main__":
    main()
