{ lab, ... }:

{
  virtualisation.oci-containers.containers.excalidraw = lab.mkContainer {
    image = "ghcr.io/yctimlin/mcp_excalidraw-canvas:sha-713706e";
    traefik = {
      name = "excalidraw";
      port = 3000;
    };
  };
}
