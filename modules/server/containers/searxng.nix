{ lab, ... }:

{
  # Internal only: n8n reaches it at http://searxng:8080.
  virtualisation.oci-containers.containers.searxng = lab.mkContainer {
    image = "ghcr.io/searxng/searxng:latest";
    volumes = [ "${./searxng/settings.yml}:/etc/searxng/settings.yml:ro" ];
    environmentFiles = [ "${lab.secrets}/searxng.env" ];
  };
}
