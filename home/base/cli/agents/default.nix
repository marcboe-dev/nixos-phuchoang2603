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
    ./excalidraw.nix
  ];

  home.packages = with pkgs; [
    pi-coding-agent
    openspec
  ];
  # Shared MCP Servers
  programs.mcp = {
    enable = true;
    servers = {
      executor = {
        url = "https://mcp.${gatewayDomain}/mcp?mode=passthrough";
      };
    };
  };

  # Shared Skills
  programs.codex.skills = agentSkills;
  programs.cursor-agent.skillsDir = agentSkills;

  # Shared Context
  programs.codex.context = sharedContext;
  programs.cursor-agent.rules.global-context = ''
    ---
    alwaysApply: true
    ---
    ${builtins.readFile sharedContext}
  '';
}
