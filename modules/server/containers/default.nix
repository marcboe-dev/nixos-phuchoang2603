{
  imports = [
    ./traefik.nix
    ./vaultwarden.nix
    ./karakeep.nix
    ./n8n.nix
    ./n8n-sandbox.nix
    ./searxng.nix
    ./newt.nix
    ./socat.nix
    ./cliproxyapi.nix
    ./executor.nix
    ./obscura.nix
    ./excalidraw.nix
  ];

  _module.args.lab = import ./lab.nix;
}
