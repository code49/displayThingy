{ pkgs ? import <nixpkgs> {} }:

let
  unstable = import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/nixos-unstable.tar.gz") {};
in
pkgs.mkShell {
  buildInputs = [
    unstable.gemini-cli
    pkgs.openssh
    (pkgs.python3.withPackages (python-pkgs: [
      python-pkgs.pandas
      python-pkgs.spotipy
      python-pkgs.python-dotenv
      python-pkgs.matplotlib
      python-pkgs.pygame
      python-pkgs.requests
      python-pkgs.pytz
    ]))
  ];

  shellHook = ''
    echo "Spotify API Development Environment Loaded!"
    echo "Python version: $(python --version)"
    echo "Gemini CLI version: $(gemini --version 2>/dev/null || echo 'available')"
    
    # Optional: Automatically load your .env file into the shell session
    if [ -f .env ]; then
      export $(echo $(cat .env | sed 's/#.*//g' | xargs) | envsubst)
    fi
  '';
}
