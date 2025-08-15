# SPDX-FileCopyrightText: NONE
#
# SPDX-License-Identifier: CC0-1.0

{ lib,
fetchFromGitHub,
python3Packages,
}:

python3Packages.buildPythonPackage rec {
  pname = "basic-colormath";
  version = "0.5";
  pyproject = true;

  src = fetchFromGitHub {
    owner =  "ShayHill";
    repo = "basic_colormath";
    rev = "${version}.0";
    hash = "sha256-emID56G8B3uhTcqKXWeukv85FRBodMQ6178goUs9mOY=";
  };
 
  dependencies = with python3Packages; [
    setuptools
    setuptools-scm
  ];

  build-system = with python3Packages; [
    setuptools
  ];

  outputs = [
    "out"
  ];

  nativeCheckInputs = [
    # we build without numpy -> vector tests fail
    # python3Packages.pytestCheckHook
  ];

  meta = {
    homepage = "https://github.com/ShayHill/basic_colormath";
    description = "Basic functionality of colormath";
    license = lib.licenses.mit;
  };
}
