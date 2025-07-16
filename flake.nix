{
  description = "dj-babel Python package";

  inputs = {
    nixpkgs.url = github:NixOS/nixpkgs/nixos-25.05;
  };

  outputs = { self, nixpkgs }:
    let supportedSystems = [ "x86_64-linux" ];
        forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
        pkgs = forAllSystems (system: nixpkgs.legacyPackages.${system});
    in  {

      packages = forAllSystems (system: rec {

        basic-colormath = pkgs.${system}.callPackage ./deps/basic-colormath { };
        
        djbabel = pkgs.${system}.callPackage ./. { inherit basic-colormath; };

        default = djbabel;
        
      });

      devShells = forAllSystems (system: rec {

        develop = pkgs.${system}.mkShell {
          packages = [
            (pkgs.${system}.python3.withPackages (ps: with ps; [
              self.packages.${system}.basic-colormath
              ipython
              mutagen
              pillow
              pytest
            ]))
          ];
        };

        release = pkgs.${system}.mkShell {
          packages = [
            pkgs.${system}.hatch
            pkgs.${system}.sphinx
            (pkgs.${system}.python3.withPackages (ps: with ps; [
              # dependencies
              self.packages.${system}.basic-colormath
              mutagen
              pillow # only used in ./src/djbabel/serato/overview.py
              pytest
            ]))
          ];
        };

        default = develop;

      });
    };
}
