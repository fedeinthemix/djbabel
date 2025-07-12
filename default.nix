# SPDX-FileCopyrightText: 2025 Federico Beffa <beffa@fbengineering.ch>
#
# SPDX-License-Identifier: CC0-1.0

{ lib,
# buildPythonPackage,
python3Packages,
# python,
# hatchling,
basic-colormath,
}:

python3Packages.buildPythonPackage rec {
  pname = "djbabel";
  version = builtins.readFile ./VERSION;
  pyproject = true;

  src = ./.;
 
  dependencies = with python3Packages; [
    basic-colormath
    mutagen
    pillow
  ];

  build-system = [ python3Packages.hatchling ];

  outputs = [
    "out"
    # "doc"
  ];

  nativeCheckInputs = [
    python3Packages.pytestCheckHook
    # python3Packages.sphinxHook
  ];

  meta = {
    homepage = "https://gitlab.com/fbengineering/djbabel";
    description = "DJ libraries conversion tool";
    license = lib.licenses.gpl3Plus;
  };
}
