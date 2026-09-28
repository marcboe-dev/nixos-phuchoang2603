---
name: talos-k8s
description: Access Felix's Talos Kubernetes clusters (dev and prod) with the local kubeconfigs. Use when the user asks about k8s, kubectl, helm, nodes, pods, Argo CD, Longhorn, Cilium, or the talos-proxmox clusters.
---

# Talos Kubernetes access

Two independent Talos Kubernetes environments, `dev` and `prod`, from `talos-proxmox`. Each has its own local Argo CD and manages only itself; there is no separate `argocd` management cluster. Do **not** use the default kubeconfig. Always pass `--kubeconfig` (or set `KUBECONFIG`) for the named environment.

Kubeconfigs (already fetched, keep them out of git):

| Env | File | Context | API VIP | Cluster name |
| --- | --- | --- | --- | --- |
| dev | `$HOME/.kube/talos-dev.yaml` | `admin@dev-talos` | `https://10.69.11.10:6443` | `dev-talos` |
| prod | `$HOME/.kube/talos-prod.yaml` | `admin@prod-talos` | `https://10.69.12.10:6443` | `prod-talos` |

If the user names an environment, use that file. If they do not, ask—or default to **dev**. Never point kubectl at prod unless they asked for prod.

## Fetching kubeconfigs via Doppler

Kubeconfigs and Talos configurations are stored as secrets in the Doppler project `talos-proxmox` under configs `dev` and `prod`.

```bash
# Login once if needed
doppler login

# Fetch kubeconfig for a specific cluster:
mkdir -p "$HOME/.kube"
doppler secrets get KUBECONFIG --plain --project talos-proxmox --config dev > "$HOME/.kube/talos-dev.yaml"
chmod 600 "$HOME/.kube/talos-dev.yaml"

# Or refresh both environment kubeconfigs at once:
mkdir -p "$HOME/.kube"
for env in dev prod; do
  doppler secrets get KUBECONFIG --plain --project talos-proxmox --config "$env" > "$HOME/.kube/talos-$env.yaml"
  chmod 600 "$HOME/.kube/talos-$env.yaml"
done

# Talosctl configs (for node-level maintenance):
mkdir -p "$HOME/.talos"
for env in dev prod; do
  doppler secrets get TALOSCONFIG --plain --project talos-proxmox --config "$env" > "$HOME/.talos/config-$env.yaml"
  chmod 600 "$HOME/.talos/config-$env.yaml"
done
```

One-off command without saving:

```bash
doppler run --project talos-proxmox --config dev -- kubectl get nodes
```

## Cluster usage

```bash
export KUBECONFIG="$HOME/.kube/talos-dev.yaml"
kubectl get nodes
kubectl get pods -A
```

Same pattern with an explicit flag:

```bash
kubectl --kubeconfig "$HOME/.kube/talos-prod.yaml" get ns
helm --kubeconfig "$HOME/.kube/talos-dev.yaml" list -A
```

Shell aliases on this machine: `k` = kubectl, `h` = helm, `kx`/`kn` = kubie.

## Inventory (from talos-proxmox)

Control-plane **node IPs** (Talos API). Kubernetes VIP is **only** for kube-apiserver. `talosctl` must use node IPs, not the VIP.

### dev

- VIP `10.69.11.10`, L2 pool `10.69.11.128-10.69.11.254`
- Control plane: `dev-server1` `10.69.11.11` (GPU passthrough)
- Default StorageClass: local-path (no Longhorn)
- GPU stack: NVIDIA GPU Operator + NVIDIA DRA Driver

### prod

- VIP `10.69.12.10`, L2 pool `10.69.12.128-10.69.12.254`
- Control plane: `prod-server1` `10.69.12.11`, `prod-server2` `10.69.12.12`, `prod-server3` `10.69.12.13`
- Longhorn storage nodes: `prod-longhorn1` `10.69.12.21`, `prod-longhorn2` `10.69.12.22`, `prod-longhorn3` `10.69.12.23`; Longhorn UI `http://10.69.12.128`
- Worker + GPU: `prod-worker1` `10.69.12.31`

## Application architecture (talos-proxmox)

Repository is typically at `~/repos/talos-proxmox` (or sibling `../talos-proxmox`).

- **Provisioning (`terraform/cluster/` and `terraform/platform/`)**: OpenTofu creates cluster infrastructure and bootstraps Gateway API CRDs, Cilium, ESO authentication, and Argo CD independently in each environment.
- **Argo CD (`apps/argocd/`)**: Each environment's local Argo CD reconciles its root platform Application and child Applications from `apps/argocd/platform/`.
- **Components (`apps/components/`)**: External Secrets, Cilium network configuration, metrics-server, Talos CCM, autoscaler, operators, GPU components, observability, and Cloudflare tunnel run in both environments. Dev uses local-path storage; prod uses Longhorn.
- The Argo CD UI Gateway and HTTPRoute are in the bootstrap chart. Current UI addresses are `http://10.69.11.254` (dev) and `http://10.69.12.254` (prod).

For setup, current addresses, and troubleshooting, consult `~/repos/talos-proxmox/docs/operations/cluster-access.md` and `docs/architecture/gitops.md`.

## Safety

- Read-first: `get`, `describe`, `logs`, `helm list`. Confirm before `apply`, `delete`, `drain`, or Helm upgrades.
- Treat kubeconfigs as secrets. Do not paste certificate data into chat.
- Prefer namespaced queries. For Argo CD applications, use the selected environment's kubeconfig; Argo CD is local to each cluster.
