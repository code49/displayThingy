{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    (pkgs.python3.withPackages (python-pkgs: [
      python-pkgs.pandas
      python-pkgs.spotipy
      python-pkgs.python-dotenv
      python-pkgs.matplotlib
      python-pkgs.pygame
      python-pkgs.requests
    ]))
  ];

  shellHook = ''
    echo "Spotify API Development Environment Loaded!"
    echo "Python version: $(python --version)"
    
    # Optional: Automatically load your .env file into the shell session
    if [ -f .env ]; then
      export $(echo $(cat .env | sed 's/#.*//g' | xargs) | envsubst)
    fi
  '';
}
