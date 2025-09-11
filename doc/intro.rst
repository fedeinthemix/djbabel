.. SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
..
.. SPDX-License-Identifier: CC-BY-4.0

Introduction
============

*djbabel* converts playlists between various DJ software. At the moment it supports:

* Traktor Pro 4
* Serato DJ Pro
* Rekordbox 7

djbabel is generally safe to use as it doesn't modify any file in use by the various DJ software. The exception is when converting *to* Serato DJ Pro. That's because Serato stores its information in audio files metadata tags. Therefore, when targeting Serato DJ Pro, djbabel writes these tags. In all other cases, the output of the program is a new playlist file in a format understood by the target software. The generated playlist can then be imported in the DJ software collection as usual.

Basic Usage
-----------

*djbabel* is a command line tool (CLI). As a simple example, to convert from a Serato DJ Pro playlist (Crate) to a Traktor Pro 4 playlist you run the following command::

djbabel -s sdjpro -t traktor4 /path/to/playlist_name.crate

In this example, it will create a file named ``playlist_name.nml`` in the directory where you run the command.

For more details run ``djbabel -h``. For help on how to import and export playlists consult the :doc:`use` page, and the documentation of your software.

Limitations
-----------

Currently only MP3, M4A, and FLAC files are supported.

..  LocalWords:  djbabel Serato Traktor
