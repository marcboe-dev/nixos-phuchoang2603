{
  imports = [
    ./traefik.nix
    ./vaultwarden.nix
    ./karakeep.nix
    ./n8n.nix
    ./newt.nix
    ./socat.nix
    ./cliproxyapi.nix
    ./mcpjungle.nix
    ./obscura.nix
  ];

  _module.args.lab = import ./lab.nix;
}
