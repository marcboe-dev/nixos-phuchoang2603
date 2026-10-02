{ lab, ... }:

{
  virtualisation.oci-containers.containers.n8n = lab.mkContainer {
    image = "docker.n8n.io/n8nio/n8n";
    volumes = [ "${lab.appdata}/ai-stack/n8n/storage:/home/node/.n8n:rw" ];
    environment = {
      DOMAIN_NAME = "phuchoang.sbs";
      SUBDOMAIN = "n8n.vps";
      SSL_EMAIL = "xuanphuc.a1gv@gmail.com";
      N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS = "true";
      N8N_PORT = "5678";
      N8N_PROTOCOL = "http";
      N8N_RUNNERS_ENABLED = "true";
      N8N_SECURE_COOKIE = "false";
      N8N_SKIP_AUTH_ON_OAUTH_CALLBACK = "true";
      N8N_HOST = lab.fqdn "n8n";
      WEBHOOK_URL = "https://n8n.vps.phuchoang.sbs/";
    };
    traefik = {
      name = "n8n";
      port = 5678;
    };
  };
}
