# Kubernetes Goat Scenario Coverage Map

Routing: read this when validating against [Kubernetes Goat](https://madhuakula.com/kubernetes-goat/) or proving "this skill detects scenario N".

| # | Scenario | Phase | How We Detect It |
|---|----------|-------|-----------------|
| 1 | Sensitive keys in codebases | 7d | .git exposure scan in running containers |
| 2 | DIND/containerd exploitation | 5a | Container runtime socket discovery + exploit |
| 3 | SSRF in K8s pod | 9d, 9e | Cloud metadata SSRF + K8s DNS service discovery |
| 4 | Container escape to host | 5b, 5c | Privileged escape via chroot + hostPath abuse |
| 5 | Docker CIS benchmarks | 10b | docker-bench-security audit |
| 6 | K8s CIS benchmarks | 10a | kube-bench CIS audit |
| 7 | Private registry attack | 8f | Registry /v2/_catalog + manifest env var extraction |
| 8 | NodePort exposed services | 2 | NodePort service enumeration + probing |
| 10 | Crypto miner in container | 8c, 8e | Image layer inspection + process monitoring |
| 11 | Namespace bypass | 9b, 9c | Cross-namespace connectivity test |
| 12 | Environment info gathering | 7c | Env var + mount + proc enumeration from inside pod |
| 13 | DoS via resources | 11e, 4 | LimitRange/ResourceQuota/resource limits audit |
| 14 | Hacker container | 6b, 11a | Pod creation RBAC + admission controller check |
| 15 | Hidden in layers | 8c, 8d | docker history + docker save layer extraction + dive |
| 16 | RBAC misconfiguration | 6a-6d | Full RBAC audit + SA token API testing |
| 17 | KubeAudit defense | 11a | Check for audit tools presence |
| 18 | Falco runtime detection | 11c | Check for Falco DaemonSet |
| 19 | Popeye sanitizer | 11a | Check for cluster sanitizer tools |
| 20 | NetworkPolicy defense | 9a | Check for NetworkPolicy presence |
| 21 | Tetragon/eBPF | 11c | Check for Tetragon/Cilium DaemonSet |
| 22 | Kyverno policy engine | 11a | Check for Kyverno admission webhooks |
