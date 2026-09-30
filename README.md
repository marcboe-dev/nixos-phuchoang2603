# Nix Config (NixOS + macOS)

Flake-based configuration for three hosts:

| Host            | Platform | Purpose           | Home Manager                       |
| --------------- | -------- | ----------------- | ---------------------------------- |
| `nixos-desktop` | NixOS    | Hyprland desktop  | CLI + GUI (Stylix, Hyprland stack) |
| `nixos-server`  | NixOS    | Docker/NFS server | CLI only                           |
| `macbook`       | macOS    | nix-darwin laptop | CLI + GUI (Stylix, AeroSpace)      |

## Layout

```
flake.nix                 # inputs + nixosConfigurations + darwinConfigurations
hosts/
  nixos-desktop/          # desktop system + monitor overrides
  nixos-server/           # server system + hardware config
  macbook/                # macOS system entrypoint
home/
  base/cli/               # shared CLI tools, shell, neovim, git, tmux
  base/gui/               # shared GUI (kitty, stylix theming)
  linux/                  # desktop Wayland stack (Hyprland, rofi, waybar, ...)
  darwin/                 # macOS home (AeroSpace, Karabiner)
  server/                 # server home profile (CLI only)
modules/
  common/                 # shared boot, locale, nix settings (NixOS)
  nixos/                  # desktop system modules
  server/                 # docker, nfs, ssh, containers/
  darwin/                 # nix-darwin system modules
```

## Usage

### NixOS desktop

```bash
nh os switch .#nixos-desktop
# or
sudo nixos-rebuild switch --flake .#nixos-desktop
```

### NixOS server

```bash
nh os switch .#nixos-server
# or
sudo nixos-rebuild switch --flake .#nixos-server
```

Remote apply:

```bash
nh os switch .#nixos-server \
  --build-host felix@nixos-server \
  --target-host felix@nixos-server
```

`nh os switch .` picks the configuration matching the current hostname.

### macOS

```bash
darwin-rebuild switch --flake .#macbook
```

## Fresh install (NixOS desktop)

1. Partition the disk with cfdisk (GPT, 512M EFI + ext4 root).
2. Format and mount:

```bash
sudo mkfs.fat -F 32 -n boot /dev/nvme0n1p1
sudo mkfs.ext4 -L nixos /dev/nvme0n1p2
sudo mount /dev/disk/by-label/nixos /mnt
sudo mkdir -p /mnt/boot
sudo mount /dev/disk/by-label/boot /mnt/boot
```

1. Clone and install:

```bash
sudo git clone https://github.com/phuchoang2603/nixos.git /mnt/etc/nixos
cd /mnt/etc/nixos
sudo nixos-generate-config --root /mnt --show-hardware-config | sudo tee hosts/nixos-desktop/hardware-configuration.nix
sudo nixos-install --flake .#nixos-desktop
```

For a server install, use `nixos-server` and `hosts/nixos-server/hardware-configuration.nix`.

### Docker containers

Containers are declared in Nix (`modules/server/containers/`) via `virtualisation.oci-containers` (no Compose). Traefik publishes 80/443; apps use the Docker `proxy` network.

`traefik` `vaultwarden` `karakeep` `n8n` `newt` `docker-sock-proxy` `mcpjungle` `obscura` `excalidraw`

Secrets live on NFS at `/mnt/storage/appdata/secrets/`. Copy from `modules/server/secrets-examples/` (`n8n.env` is optional extras; host/webhook are set in Nix). Traefik ACME certs: `/mnt/storage/appdata/traefik/certs/`.

MCPJungle: dashboard at `https://mcp.home.phuchoang.sbs/`, remote MCP at
`https://mcp.home.phuchoang.sbs/mcp`. Add upstreams and credentials in the
dashboard. SQLite data lives at `/var/lib/mcpjungle`.

Obscura serves HTTP MCP at `http://obscura:3000/mcp` on the internal `proxy`
network. Register it in MCPJungle as a Streamable HTTP upstream. It can access
private/LAN addresses; it has no published host port or Traefik route.

Excalidraw canvas (mcp_excalidraw) serves the web UI and REST API at
`https://excalidraw.home.phuchoang.sbs` (LAN only) and `http://excalidraw:3000` on
`proxy`. Scenes are in-memory and lost on restart. Its MCP server is stdio-only,
so MCPJungle runs the `-stdio` image and launches it via `npx`. Register it as a
stdio upstream with `mcpjungle register -c excalidraw.json`:

```json
{
  "name": "excalidraw",
  "transport": "stdio",
  "description": "Live Excalidraw canvas at https://excalidraw.home.phuchoang.sbs",
  "session_mode": "stateful",
  "command": "npx",
  "args": ["-y", "mcp-excalidraw-server@2.0.0"],
  "env": {
    "EXPRESS_SERVER_URL": "http://excalidraw:3000",
    "EXCALIDRAW_NO_AUTOSTART": "1"
  }
}
```

Agents get `EXPRESS_SERVER_URL` pointing at the canvas and the `excalidraw-skill`
skill, so the CLI (`npx -y mcp-excalidraw-server@2.0.0 export --out ...`) can
export diagrams into local repos. Keep the canvas open in a browser tab for
screenshots and Mermaid conversion.

`excalidraw-icon` (installed with the agents module) places logos/icons from
[svgl](https://svgl.app) (`svgl:docker`) and [Iconify](https://icon-sets.iconify.design)
(`selfhst:proxmox`, `logos:kubernetes`, `mdi:server`) on the canvas as image
elements: `excalidraw-icon search <query>`, then
`excalidraw-icon add <ref> --x 100 --y 100 --label Name`.
Set `OBSCURA_MCP_TOKEN` in `/mnt/storage/appdata/secrets/obscura.env` to a
random value of at least 32 bytes before starting it (see `modules/server/secrets-examples/obscura.env`).

The dashboard requires unauthenticated development mode. Traefik restricts
external access to `10.69.0.0/16`, but containers on `proxy` bypass that
restriction. MCPJungle does not restrict outbound upstreams (SSRF); only use
this setup with trusted LAN/VPN clients and containers.

```bash
sudo systemctl restart docker-traefik
sudo systemctl status 'docker-*'
```
