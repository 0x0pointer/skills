# MITRE ATT&CK Coverage — Container & K8s Security

Routing: read this when reporting findings, threat-modeling, or filling out a coverage matrix and you need the ATT&CK technique ID for a specific test.

| Technique | ID | What we test |
|-----------|----|-------------|
| Exploit Public-Facing App | T1190 | Exposed K8s API server, Docker daemon, etcd, kubelet, registries, NodePort services |
| Deploy Container | T1610 | Unauthorized container/pod creation, hacker container deployment |
| Container Admin Command | T1609 | Exec into containers, kubectl abuse, kubelet /run endpoint RCE |
| Escape to Host | T1611 | Container breakout via privileged mode, hostPath, chroot, Docker/containerd socket, capabilities |
| Container Image Discovery | T1613 | Image enumeration, private registry /v2/_catalog, image layer inspection |
| Unsecured Credentials in Files | T1552.007 | Service account tokens, secrets in env vars, secrets in image layers, .git exposure |
| Network Service Discovery | T1046 | Cross-namespace scanning, internal service discovery via K8s DNS |
| Cloud Instance Metadata | T1552.005 | SSRF to 169.254.169.254, cloud credential theft |
| Resource Hijacking | T1496 | Crypto miner detection in containers and image layers |
| Account Discovery | T1087 | RBAC enumeration, ClusterRoleBinding audit, SA permission escalation |
