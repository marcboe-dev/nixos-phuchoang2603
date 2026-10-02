{ config, lab, ... }:

let
  tls = "${lab.appdata}/ai-stack/n8n/sandbox-tls";
  apiImage = "ghcr.io/n8n-io/n8n-sandbox-service-api:latest";
  envFile = "${lab.secrets}/n8n-sandbox.env";
  # Certificates are issued for these hostnames, so the container names must match.
  units = [
    "docker-sandbox-api.service"
    "docker-sandbox-runner-1.service"
  ];
in
{
  systemd.tmpfiles.rules = [ "d ${tls} 0755 root root -" ];

  systemd.services.n8n-sandbox-certs = {
    description = "Generate n8n sandbox mTLS certificates";
    after = [ "docker.service" ];
    requires = [ "docker.service" ];
    before = units;
    requiredBy = units;
    path = [ config.virtualisation.docker.package ];
    unitConfig.ConditionPathExists = "!${tls}/api/ca.crt";
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      docker run --rm --user 0:0 --entrypoint sh \
        -e NUM_RUNNERS=1 -v ${tls}:/tls ${apiImage} -c \
        'bootstrap-mtls.sh --out-dir /tls --api-san sandbox-api --control-san-prefix sandbox-runner && chown -R sandbox-api:sandbox-api /tls/api'
    '';
  };

  # Internal only: never route Traefik to these. The runner is privileged Docker-in-Docker.
  virtualisation.oci-containers.containers = {
    sandbox-api = lab.mkContainer {
      image = apiImage;
      volumes = [ "${tls}:/tls:ro" ];
      environmentFiles = [ envFile ];
      environment = {
        SANDBOX_API_GRPC_TLS_CERT_FILE = "/tls/api/grpc-server.crt";
        SANDBOX_API_GRPC_TLS_KEY_FILE = "/tls/api/grpc-server.key";
        SANDBOX_API_GRPC_TLS_CLIENT_CA_FILE = "/tls/api/ca.crt";
        SANDBOX_API_RUNNER_CONTROL_GRPC_TLS_CA_FILE = "/tls/api/ca.crt";
        SANDBOX_API_RUNNER_CONTROL_GRPC_TLS_CERT_FILE = "/tls/api/control-grpc-api-client.crt";
        SANDBOX_API_RUNNER_CONTROL_GRPC_TLS_KEY_FILE = "/tls/api/control-grpc-api-client.key";
        SANDBOX_API_RUNNER_CONTROL_GRPC_TLS_SERVER_NAME = "sandbox-runner-1";
      };
    };

    sandbox-runner-1 = lab.mkContainer {
      image = "ghcr.io/n8n-io/n8n-sandbox-service-runner-dind:latest";
      dependsOn = [ "sandbox-api" ];
      extraOptions = [ "--privileged" ];
      volumes = [ "${tls}:/tls:ro" ];
      environmentFiles = [ envFile ];
      environment = {
        SANDBOX_RUNNER_API_GRPC_ADDR = "sandbox-api:9090";
        SANDBOX_RUNNER_HTTP_BASE_URL = "http://sandbox-runner-1:8080";
        SANDBOX_RUNNER_CONTROL_GRPC_LISTEN_ADDR = ":9091";
        SANDBOX_RUNNER_CONTROL_GRPC_ADVERTISE_ADDR = "sandbox-runner-1:9091";
        SANDBOX_RUNNER_ID = "runner-1";
        SANDBOX_RUNNER_DOCKER_SANDBOX_IMAGE = "ghcr.io/n8n-io/n8n-sandbox-service-sandbox:latest";
        SANDBOX_RUNNER_REGISTRATION_GRPC_CA_FILE = "/tls/runner/ca.crt";
        SANDBOX_RUNNER_REGISTRATION_GRPC_CERT_FILE = "/tls/runner/grpc-client.crt";
        SANDBOX_RUNNER_REGISTRATION_GRPC_KEY_FILE = "/tls/runner/grpc-client.key";
        SANDBOX_RUNNER_REGISTRATION_GRPC_SERVER_NAME = "sandbox-api";
        SANDBOX_RUNNER_CONTROL_GRPC_TLS_CERT_FILE = "/tls/runner/control-grpc-server.crt";
        SANDBOX_RUNNER_CONTROL_GRPC_TLS_KEY_FILE = "/tls/runner/control-grpc-server.key";
        SANDBOX_RUNNER_CONTROL_GRPC_TLS_CLIENT_CA_FILE = "/tls/runner/ca.crt";
      };
    };
  };
}
