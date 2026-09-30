{ lab, ... }:

{
  virtualisation.oci-containers.containers.excalidraw = lab.mkContainer {
    image = "ghcr.io/yctimlin/mcp_excalidraw-canvas:sha-713706e";
    traefik = {
      name = "excalidraw";
      port = 3000;
    };
    labels = {
      "traefik.http.middlewares.excalidraw-lan.ipallowlist.sourcerange" = "10.69.0.0/16";
      "traefik.http.routers.excalidraw.middlewares" = "excalidraw-lan@docker";
    };
  };
}
