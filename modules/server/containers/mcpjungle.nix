{ lab, ... }:

let
  data = "/var/lib/mcpjungle";
in
{
  systemd.tmpfiles.rules = [ "d ${data} 0700 root root -" ];

  virtualisation.oci-containers.containers.mcpjungle = lab.mkContainer {
    image = "ghcr.io/mcpjungle/mcpjungle:0.4.6";
    volumes = [ "${data}:/data:rw" ];
    environment = {
      SERVER_MODE = "development";
      SQLITE_DB_PATH = "/data/mcpjungle.db";
      OTEL_ENABLED = "false";
    };
    traefik = {
      name = "mcp";
      port = 8080;
    };
    labels = {
      "traefik.http.middlewares.mcp-lan.ipallowlist.sourcerange" = "10.69.0.0/16";
      "traefik.http.routers.mcp.middlewares" = "mcp-lan@docker";
    };
  };
}
