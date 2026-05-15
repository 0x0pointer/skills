# OWASP Kubernetes Top 10 Coverage Matrix

Routing: read this when checking K8s Top 10 compliance, mapping a finding to the OWASP K-number, or planning which phase of the workflow exercises which category.

| # | Category | Phase | Tests |
|---|----------|-------|-------|
| K01 | Insecure Workload Configuration | 4, 5 | Privileged pods, host namespaces (PID/IPC/Net), hostPath mounts, root containers, missing readOnlyRootFilesystem, dangerous capabilities (SYS_ADMIN, SYS_PTRACE, NET_RAW, AUDIT_CONTROL), missing seccomp/AppArmor profiles |
| K02 | Supply Chain Vulnerabilities | 7, 8 | Image scanning (Trivy), unsigned images, untrusted registries, image layer secret extraction (docker history, docker save, dive), crypto miner payloads in images, .git exposure in container images |
| K03 | Overly Permissive RBAC | 6 | ClusterRoleBindings to cluster-admin, wildcard permissions, service account abuse, SA token API probing, missing resourceNames restrictions, pod creation RBAC |
| K04 | Lack of Centralized Policy Enforcement | 11 | Missing admission controllers (OPA/Gatekeeper, Kyverno, PodSecurity), missing PodSecurityStandards enforcement, ability to deploy arbitrary images |
| K05 | Inadequate Logging and Monitoring | 11 | Missing audit logging (--audit-log-path), missing runtime security (Falco, Tetragon), no anomaly detection |
| K06 | Broken Authentication Mechanisms | 3, 5 | API server anonymous auth, kubelet anonymous auth + /run RCE, default service account auto-mount, bootstrap tokens, etcd unauthenticated access |
| K07 | Missing Network Segmentation | 9 | Missing NetworkPolicies, cross-namespace pod connectivity, flat network exploitation, NodePort exposure |
| K08 | Secrets Management Failures | 7 | Secrets as env vars (not volume mounts), unencrypted etcd, secrets in git/codebases, secrets in image layers, plaintext secrets in manifests, missing external secrets operator |
| K09 | Misconfigured Cluster Components | 3, 10 | API server flags (--anonymous-auth, --allow-privileged, --authorization-mode), kubelet config, etcd encryption, kube-bench CIS audit, docker-bench-security audit |
| K10 | Outdated and Vulnerable K8s Components | 3, 8 | K8s version CVEs, addon versions, container image CVEs (Trivy), EOL base images |
