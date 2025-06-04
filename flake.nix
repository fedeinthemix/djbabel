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
        
        djbabel = pkgs.${system}.callPackage ./. { };

        default = djbabel;
        
      });

      devShells = forAllSystems (system: rec {

        develop = pkgs.${system}.mkShell {
          packages = [
            (pkgs.${system}.python3.withPackages (ps: with ps; [
              pytest
              ipython
              mutagen
              pillow
            ]))
          ];
        };

        release = pkgs.${system}.mkShell {
          packages = [
            (pkgs.${system}.python3.withPackages (ps: with ps; [
              # dependencies
              mutagoen
              pillow
              pytest
            ]))
          ];
        };

        default = develop;

      });
    };
}
