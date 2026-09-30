{ pkgs, ... }:

let
  gatewayDomain = (import ../../../../modules/server/lib.nix).domain;

  mkPythonScript =
    name:
    pkgs.writers.writePython3Bin name {
      flakeIgnore = [ "E501" ];
    } (builtins.readFile ./scripts/${name}.py);
in
{
  home.packages = map mkPythonScript [
    "excalidraw-icon"
    "excalidraw-connect"
  ];

  home.sessionVariables.EXPRESS_SERVER_URL = "https://excalidraw.${gatewayDomain}";
}
