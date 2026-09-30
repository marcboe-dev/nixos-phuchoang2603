{ pkgs, ... }:

let
  gatewayDomain = (import ../../../../modules/server/lib.nix).domain;

  excalidrawIcon = pkgs.writers.writePython3Bin "excalidraw-icon" {
    flakeIgnore = [ "E501" ];
  } (builtins.readFile ./scripts/excalidraw-icon.py);
in
{
  home.packages = [ excalidrawIcon ];

  home.sessionVariables.EXPRESS_SERVER_URL = "https://excalidraw.${gatewayDomain}";
}
