{ pkgs, ... }:

let
  sharedContext = ./AGENTS.md;
  agentSkills = ./skills;
  gatewayDomain = (import ../../../../modules/server/lib.nix).domain;
in
{
  imports = [
    ./cursor.nix
    ./codex.nix
    ./t3code.nix
  ];

  home.packages = with pkgs; [
    pi-coding-agent
    openspec
  ];

  home.sessionVariables.EXPRESS_SERVER_URL = "https://excalidraw.${gatewayDomain}";

  # Shared MCP Servers
  programs.mcp = {
    enable = true;
    servers = {
      mcpjungle = {
        url = "https://mcp.${gatewayDomain}/mcp";
      };
    };
  };

  # Shared Skills
  programs.codex.skills = agentSkills;
  programs.cursor-agent.skillsDir = agentSkills;

  # Shared Context
  programs.codex.context = sharedContext;
  programs.cursor-agent.rules.global-context = sharedContext;
}
