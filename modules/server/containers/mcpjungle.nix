{ lab, ... }:

let
  data = "/var/lib/mcpjungle";
in
{
  systemd.tmpfiles.rules = [
    "d ${data} 0700 root root -"
    "d ${data}/npm 0700 root root -"
  ];

  virtualisation.oci-containers.containers.mcpjungle = lab.mkContainer {
    image = "ghcr.io/mcpjungle/mcpjungle:0.4.6-stdio";
    volumes = [
      "${data}:/data:rw"
      "${data}/npm:/root/.npm:rw"
    ];
    environment = {
      SERVER_MODE = "development";
      SQLITE_DB_PATH = "/data/mcpjungle.db";
      OTEL_ENABLED = "false";
      MCP_SERVER_INIT_REQ_TIMEOUT_SEC = "180";
    };
    traefik = {
      name = "mcp";
      port = 8080;
    };
  };
}
