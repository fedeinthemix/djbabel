# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import platform
import re
import subprocess
from pathlib import Path
import json
import warnings
from dataclasses import Field

from ..types import AMarkerType

#######################################################################
# Mappings

# Map AMarkerType into the corresponding Rekordbox number
# 4: Grid / Beat Marker / AutoGrid (Used for automatic beatgrid markers)
TRAKTOR_MARKERTYPE_MAP = {
    AMarkerType.CUE : "0",
    AMarkerType.FADE_IN : "1",
    AMarkerType.FADE_OUT : "2",
    AMarkerType.CUE_LOAD : "3",
    AMarkerType.LOOP : "5"
}

# Includes mapping of fields from ATrack to the Traktor Pro 4 NML name of
# only those fields:
# 1) Whose mapping is not a simple conversion to UPPERCASE.
# 2) Are not used. In this case the name maps to None
# The later are mapped via a function.
TRAKTOR_FIELD_NAMES_MAP = {
    # 'title',
    # 'artist',
    # 'composer',
    'album' : 'TITLE', # TAG, this is the title in ALBUM
    'grouping' : None,
    # 'genre',
    # 'aformat',
    'size' : 'FILESIZE',
    'total_time' : 'PLAYTIME', # PLAYTIME_FLOAT is also added
    # 'disc_number', in ALBUM TAG
    'track_number': 'TRACK', # in ALBUM TAG
    # 'release_date',
    'average_bpm' : 'BPM', # in TEMPO TAG
    'date_added' : 'IMPORT_DATE',
    'bit_rate' : 'BITRATE', # XXX for VBR set ot -1
    'sample_rate' : None,
    'comments' : 'COMMENT',
    'play_count' : 'PLAYCOUNT',
    # 'rating',
    # 'location', # IS a TAG
    # 'remixer',
    'tonality' : 'VALUE', # in MUSICAL_KEY tag, rather than the one in info.
    # 'label',
    'mix' : None,
    # 'data_source',
    # 'markers',
    # 'beatgrid',
    'locked' : 'LOCK',
    # 'color',
    'trackID' : None,
    # 'loudness'
}

#########################################################################

def make_is_tag_attr_predicate(fns: list[str]):
    """Construct a predicate taking a field and checking if its name is in a list.
    """
    def predicate(f: Field | str) -> bool:
        n = f.name if isinstance(f, Field) else f
        if n in fns:
            return True
        else:
            return False

    return predicate

is_album_tag_attr =  make_is_tag_attr_predicate(['track_number', 'disc_number', 'album'])
is_entry_tag_attr = make_is_tag_attr_predicate(['title', 'artist', 'locked'])
is_location_tag_attr = make_is_tag_attr_predicate(['location'])
is_tempo_tag_attr = make_is_tag_attr_predicate(['average_bpm'])
is_musical_key_attr = make_is_tag_attr_predicate(['tonality'])
is_loudness_tag_attr = make_is_tag_attr_predicate(['loudness'])
is_cue_v2_tag_attr = make_is_tag_attr_predicate(['marker', 'beatgrid'])

def is_info_tag_attr(f: Field | str) -> bool:
    if not (is_album_tag_attr(f) or is_entry_tag_attr(f) or is_location_tag_attr(f) or is_tempo_tag_attr(f) or is_musical_key_attr(f) or is_loudness_tag_attr(f) or is_cue_v2_tag_attr(f)):
        return True
    else:
        return False


def traktor_attr_name(s: str) -> str | None:
    """Convert an ATrack field name (as a string) into the name used by Traktor.
    """
    if s in TRAKTOR_FIELD_NAMES_MAP.keys():
        return TRAKTOR_FIELD_NAMES_MAP[s]
    else:
        return s.upper()


#########################################################################

def traktor_path(p: Path) -> str:
    """Replaces path delimiter with '/:', and remove Windows drive.
    """
    if not p.is_absolute():
        fpath = p.resolve()
    else:
        fpath = p
    f = fpath.name
    # On Windows the 1st part is the anchor ( drive + root)
    # On POSIX it's the root that we re-add in 'td'
    d = fpath.parent.parts[1:]
    td = '/' + '/'.join([f":{c}" for c in d]) + '/:'
    return td + f

###### VOLUME AND VOLUMEID ######

def _get_volume_id_windows(drive: str) -> str:
    """
    Retrieves the Windows volume serial number for a given drive.
    """
    try:
        result = subprocess.run(
            f"vol {drive}",
            capture_output=True,
            text=True,
            shell=True,
            check=True
        )
        match = re.search(r"Volume Serial Number is ([0-9A-F]{4})-([0-9A-F]{4})", result.stdout, re.IGNORECASE)
        if match:
            return match.group(1) + match.group(2)
        else:
            warnings.warn(f'Failed to get volume seria for {drive} (Windows)')
            return ''
    except subprocess.CalledProcessError as e:
        warnings.warn(f"Command 'vol {drive}:' failed: {e.stderr.strip()}")
        return ''
    except Exception as e:
        warnings.warn(f"Could not get volume serial for {drive} (Windows): {e}")
        return ''


# Recursive helper to check devices and their children
def find_longest_matching_uuid(path: Path, device_node, current_best_len, current_best_uuid, current_best_name) -> tuple[int,str,str]:
    
    if 'mountpoint' in device_node and device_node['mountpoint'] is not None:
        mount_point_path = Path(device_node['mountpoint'])

        if path.is_relative_to(mount_point_path):
            if 'uuid' in device_node and device_node['uuid']:
                if len(str(mount_point_path)) > current_best_len:
                    return len(str(mount_point_path)), device_node['uuid'], device_node['name']

    if 'children' in device_node:
        for child in device_node['children']:
            current_best_len, current_best_uuid, current_best_name = find_longest_matching_uuid(path, child, current_best_len, current_best_uuid, current_best_name)
                        
    return current_best_len, current_best_uuid, current_best_name


def _get_vol_volid_linux(path: Path) -> tuple[str,str]:
    """
    Gets the label and UUID of the volume a given file resides on Linux.
    """
    try:
        # 1. Use lsblk to find the filesystem containing the file
        lsblk_output = subprocess.check_output(["lsblk", "-J", "-o", "UUID,NAME,MOUNTPOINT"],
                                               text=True,
                                               stderr=subprocess.PIPE)
        
        lsblk_data = json.loads(lsblk_output)

        # We want to find the longest matching mountpoint to ensure we get the
        # most specific volume.
        best_match_uuid = None
        best_match_len = -1
        current_best_name = ''

        for block_device in lsblk_data.get("blockdevices", []):
            best_match_len, best_match_uuid, current_best_name = find_longest_matching_uuid(path, block_device, best_match_len, best_match_uuid, current_best_name)
            
        return current_best_name, best_match_uuid if best_match_uuid is not None else ''

    except FileNotFoundError:
        warnings.warn("Error: 'lsblk' command not found.")
        return ('', '')
    except subprocess.CalledProcessError as e:
        warnings.warn(f"Could not get volume serial (Linux): {e.cmd}")
        warnings.warn(f"Stderr: {e.stderr}")
        return ('', '')
    except json.JSONDecodeError as e:
        warnings.warn(f"Could not get volume serial (Linux): {e}")
        return ('', '')
    except Exception as e:
        warnings.warn(f"Could not get volume serial (Linux): {e}")
        return ('', '')


def _get_vol_volid_macos(path: Path) -> tuple[str,str]:
    """
    Gets the volume and UUID of the volume a given file resides on macOS.
    """
    try:
        # 1. Get the mount point of the file's volume
        df_output = subprocess.check_output(["df", "-P", path],
                                            text=True,
                                            stderr=subprocess.PIPE)
        
        lines = df_output.strip().split('\n')
        if len(lines) < 2:
            warnings.warn(f"Could not get volume for {path} (macOS)")
            return ('','')

        mount_point = lines[1].split()[-1]
        volume = Path(mount_point).name

        # 2. Get the Volume UUID from the mount point using diskutil info
        diskutil_out = subprocess.check_output(["diskutil", "info", mount_point],
                                               text=True,
                                               stderr=subprocess.PIPE)
        
        volume_uuid = ''
        for line in diskutil_out.split('\n'):
            if "Volume UUID:" in line:
                volume_uuid = line.split(":", 1)[1].strip()
                break
        
        return (volume, volume_uuid)

    except subprocess.CalledProcessError as e:
        warnings.warn(f"Command {e.cmd} failed: {e.stderr.strip()}")
        return ('', '')
    except Exception as e:
        warnings.warn(f"Could not get volume serial for {path} (macOS): {e}")
        return ('', '')        


def location_volume_id(path: Path) -> tuple[str,str]:
    """
    Volume ID for a given path.
    """
    system = platform.system()

    if system == "Windows":
        return (path.drive, _get_volume_id_windows(path.drive))
    elif system == "Linux":
        return _get_vol_volid_linux(path)
    elif system == "Darwin": # macOS
        return _get_vol_volid_macos(path)
    else:
        warnings.warn(f"Error: Unsupported operating system for volume ID lookup: {system}\nUsing empty string.")
        return ('','')
