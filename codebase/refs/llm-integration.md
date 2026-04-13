# LLM Integration Security Reference

Lazy-loaded reference for Phase 5b of the `/codebase` skill. Contains framework-specific grep patterns, CVE table, MCP Top 10, and secure agent design patterns.

---

## Framework-Specific Grep Patterns

Use these to find LLM-specific code patterns. Adapt to the actual framework detected in Phase 1.

### OpenAI SDK (Python / Node)

```
# Client initialization
from openai import OpenAI | import OpenAI from "openai"
client = OpenAI(api_key=...)

# Dangerous patterns
client.chat.completions.create(  →  check for: missing max_tokens, user input in messages
client.completions.create(       →  legacy completions API — same checks
openai.api_key = "sk-..."       →  hardcoded API key

# Function calling / tools
tools=[{...}]                    →  check tool definitions for over-permissioned operations
tool_choice="auto"               →  LLM decides which tools to call — check all tool handlers
function_call=                   →  legacy function calling — same checks

# Prompt patterns to find
messages=[{"role": "system", "content": ...}]  →  read system prompts for secrets/instructions
messages.append({"role": "user", "content": user_input})  →  check if user_input is sanitized
```

### Anthropic SDK (Python / Node)

```
# Client initialization
from anthropic import Anthropic | import Anthropic from "@anthropic-ai/sdk"
client = Anthropic(api_key=...)

# Dangerous patterns
client.messages.create(          →  check for: missing max_tokens, user input in messages
model="claude-..."               →  model selection — check if user-controllable

# Tool use
tools=[{"name": ..., "input_schema": ...}]  →  check tool definitions
tool_use blocks in response      →  check how tool results are processed
```

### LangChain (Python / Node)

```
# High-risk tools — these execute arbitrary code
from langchain.tools import PythonREPLTool, ShellTool, PythonAstREPLTool
from langchain_experimental.tools import PythonREPLTool
from langchain.chains import PALChain, LLMMathChain, SQLDatabaseChain

# Agent creation — check what tools are passed
initialize_agent(tools=[...], agent=AgentType.ZERO_SHOT_REACT)
AgentExecutor(agent=..., tools=[...])
create_react_agent | create_openai_functions_agent | create_tool_calling_agent

# Prompt templates with user input
PromptTemplate.from_template("... {user_input} ...")
ChatPromptTemplate.from_messages([...])
SystemMessage(content=...) | HumanMessage(content=...)

# RAG patterns
RetrievalQA.from_chain_type(retriever=...)
ConversationalRetrievalChain
load_qa_chain | stuff_documents_chain
vectorstore.similarity_search(query)  →  check for tenant isolation filters
vectorstore.as_retriever()             →  check search_kwargs for metadata filtering

# Memory — conversation history storage
ConversationBufferMemory | ConversationSummaryMemory
ChatMessageHistory  →  check persistence and access controls

# Document loaders — ingestion pipeline
DirectoryLoader | TextLoader | PyPDFLoader | WebBaseLoader
UnstructuredFileLoader  →  check what sources are loaded, any user-controlled paths?

# Output parsers — structured output
PydanticOutputParser | JsonOutputParser  →  generally safer
output.content used directly            →  check downstream usage
```

### LlamaIndex

```
# Index creation and querying
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()

# Dangerous patterns
query_engine.query(user_input)   →  check if user_input reaches prompt without sanitization
PandasQueryEngine               →  executes generated Python code on DataFrames
NLSQLTableQueryEngine           →  generates and executes SQL from natural language
SubQuestionQueryEngine          →  multi-step — check each sub-engine

# Tool/Agent patterns
FunctionTool.from_defaults(fn=...)  →  check what functions are exposed
ReActAgent.from_tools(tools=[...])  →  check tool permissions
OpenAIAgent.from_tools(tools=[...])

# Retrievers — check for tenant isolation
VectorIndexRetriever(index, similarity_top_k=...)
index.as_retriever(filters=MetadataFilters(...))  →  good — has filters
index.as_retriever()                               →  bad — no tenant isolation
```

### Haystack

```
# Pipeline components
from haystack.components.generators import OpenAIGenerator, AnthropicGenerator
from haystack.components.builders import PromptBuilder, ChatPromptBuilder

# Dangerous patterns
PromptBuilder(template="... {{query}} ...")  →  check if query is user-controlled
pipeline.run({"prompt_builder": {"query": user_input}})

# RAG patterns
InMemoryDocumentStore | ElasticsearchDocumentStore | PineconeDocumentStore
InMemoryBM25Retriever | EmbeddingRetriever
```

### Semantic Kernel (Python / .NET)

```
# Plugin/function registration
kernel.add_plugin(plugin, plugin_name=...)
@kernel_function(description=...)  →  check function permissions
kernel.invoke(function_name, **args)

# Prompt templates
KernelPromptTemplate(template_config=...)
kernel.invoke_prompt(prompt=..., input=user_input)

# Planner — auto-generates execution plans
from semantic_kernel.planners import SequentialPlanner, ActionPlanner
planner.create_plan(goal=user_input)  →  user controls the plan goal
```

### MCP SDK (Python / Node)

```
# Server-side tool definitions
@server.tool()
async def tool_name(arguments):  →  check argument handling for injection

# Resource handlers
@server.resource("resource://path")
async def get_resource():  →  check for sensitive data exposure

# Client-side
client = ClientSession(read, write)
result = await client.call_tool(name, arguments)  →  check if response is trusted/validated

# Dangerous patterns
subprocess.run(arguments["command"])  →  command injection in tool handler
open(arguments["path"])               →  path traversal in tool handler
cursor.execute(arguments["query"])    →  SQL injection in tool handler
```

### CrewAI / AutoGen

```
# CrewAI
from crewai import Agent, Task, Crew
Agent(role=..., tools=[...], allow_delegation=True)  →  check delegation scope
Task(description=user_input)                          →  user controls task description

# AutoGen
from autogen import AssistantAgent, UserProxyAgent
UserProxyAgent(code_execution_config={"work_dir": ...})  →  arbitrary code execution
AssistantAgent(system_message=...)  →  check system prompt content
```

---

## CVE Reference Table

Known CVEs in LLM frameworks. Check detected dependency versions against this table.

| CVE | Package | Affected Versions | Severity | Pattern to grep |
|-----|---------|-------------------|----------|-----------------|
| CVE-2023-46229 | langchain | <0.0.325 | Critical | `PALChain`, `LLMMathChain` — arbitrary code execution via LLM output |
| CVE-2023-44467 | langchain | <0.0.312 | Critical | `PythonREPLTool` — no sandboxing on code execution |
| CVE-2023-39659 | langchain | <0.0.247 | Critical | `SQLDatabaseChain` — SQL injection via crafted prompts |
| CVE-2023-36189 | langchain | <0.0.236 | High | `CSVAgent` — arbitrary code execution via pandas |
| CVE-2023-36188 | langchain | <0.0.232 | Critical | SSTI in prompt templates |
| CVE-2023-38896 | langchain | <0.0.236 | High | `JSONAgent` — code execution via crafted JSON |
| CVE-2023-34541 | langchain | <0.0.205 | Critical | Arbitrary code execution via `exec()` |
| CVE-2024-3571 | langchain-experimental | <0.0.55 | High | `PythonREPLTool` — sandbox escape |
| CVE-2024-28088 | langchain | <0.1.12 | Medium | SSRF via `WebBaseLoader` |
| CVE-2024-21513 | langchain-experimental | <0.0.61 | Critical | `PythonAstREPLTool` — sandbox bypass |
| CVE-2024-27444 | langchain | <0.1.9 | High | Path traversal in `DirectoryLoader` |
| CVE-2024-46946 | langchain-experimental | <0.3.0 | Critical | `PythonREPLTool` persistent sandbox escape |
| CVE-2023-49438 | llama_index | <0.9.14 | High | SSRF in `download_loader` |
| CVE-2024-23751 | llama_index | <0.10.0 | Critical | `PandasQueryEngine` — arbitrary code execution |
| CVE-2024-4181 | haystack | <2.0 | High | Prompt injection in `PromptBuilder` |
| CVE-2024-39249 | haystack | <2.2.1 | Medium | ReDoS in component parsing |
| CVE-2024-22190 | semantic-kernel | <0.4.2 | High | Arbitrary file write via planner |

### How to use this table:
1. Read the detected package version from the manifest (Phase 1)
2. Compare against affected versions
3. If vulnerable version found: grep for the specific pattern to determine if the vulnerable code path is used
4. If the pattern is present: `report(action="finding", data={...})` with CVE ID, affected file, and vulnerable code path

---

## Secure Agent Design Patterns (Positive Checklist)

When reviewing agentic LLM code, check whether these secure design patterns are implemented. Their **absence** is a finding.

### 1. Action Selector Pattern
The LLM selects from a fixed set of pre-defined actions. The application code executes the action, not the LLM.
```
# Good: LLM picks action, app executes
action = llm.classify(user_input, options=["search", "create", "delete"])
if action == "delete":
    require_confirmation(user)
    execute_delete(validated_id)

# Bad: LLM generates and executes arbitrary code
code = llm.generate(f"Write Python code to: {user_input}")
exec(code)
```
**Check for:** Does the codebase use a fixed action dispatch instead of arbitrary code generation?

### 2. Plan-Then-Execute with Validation
The LLM generates a plan (data), which is validated and approved before execution.
```
# Good: Plan is data, validated before execution
plan = llm.generate_plan(task)
validated_plan = validate_plan(plan, allowed_actions, user_permissions)
if requires_approval(validated_plan):
    await get_human_approval(validated_plan)
execute_plan(validated_plan)
```
**Check for:** Is there a validation step between LLM planning and execution? Is human-in-the-loop present for destructive actions?

### 3. Dual LLM Pattern
A privileged LLM handles system instructions; a quarantined LLM handles untrusted input. The quarantined LLM cannot invoke tools directly.
```
# Good: Untrusted input goes to quarantined LLM
quarantined_response = quarantined_llm.process(untrusted_input)
sanitized = validate_output(quarantined_response)
privileged_response = privileged_llm.act(sanitized, tools=trusted_tools)
```
**Check for:** Is there separation between LLMs that handle untrusted input and LLMs that have tool access?

### 4. Code-Then-Execute (Sandboxed)
LLM generates code that runs in a restricted sandbox, not the host environment.
```
# Good: Sandbox with restricted permissions
result = sandbox.execute(llm_generated_code, timeout=5, allowed_imports=["math", "json"])

# Bad: Direct execution
exec(llm_generated_code)
```
**Check for:** If code execution exists, is it sandboxed? What are the sandbox constraints?

### 5. Output Validation Gate
All LLM outputs pass through a validation/sanitization layer before reaching any sink.
```
# Good: Output validated before use
raw_output = llm.generate(prompt)
validated = output_validator.validate(raw_output, expected_schema)
sanitized = sanitize_for_context(validated, target="html")  # or "sql", "shell", etc.
```
**Check for:** Is there a validation layer between LLM output and downstream usage?

---

## OWASP MCP Top 10 Quick Reference

For codebases that implement or consume MCP (Model Context Protocol) servers.

| # | Category | Code-Level Checks |
|---|----------|-------------------|
| MCP01 | Excessive Permissions | Tool handlers perform operations beyond their stated scope. Check tool descriptions vs actual handler code |
| MCP02 | Tool Injection / Manipulation | MCP tool descriptions or schemas can be modified at runtime. Check if tool metadata is dynamic or static |
| MCP03 | Command Injection | Tool arguments passed to `subprocess`, `exec`, `eval`, shell commands, or SQL without sanitization |
| MCP04 | Sensitive Data Exposure | MCP resources or tool responses expose secrets, PII, internal paths, or credentials |
| MCP05 | Insufficient Input Validation | Tool arguments not validated against schemas. No type checking, length limits, or format validation |
| MCP06 | Authentication Gaps | MCP server accessible without authentication. No API key, token, or mTLS requirement |
| MCP07 | Resource Exhaustion | No rate limiting, timeout, or resource caps on MCP tool execution |
| MCP08 | Logging & Monitoring Gaps | MCP tool invocations not logged. No audit trail for tool usage, arguments, or results |
| MCP09 | Rug Pull / Tool Redefinition | MCP server can change tool behavior between listing and invocation. No integrity verification |
| MCP10 | Third-Party Server Trust | MCP client trusts responses from remote MCP servers without validation or sanitization |

### What to grep for MCP servers:

```python
# Python MCP SDK patterns
@server.tool()           →  find all tool definitions
@server.resource()       →  find all resource definitions
@server.prompt()         →  find all prompt definitions

# In each tool handler, check:
subprocess.run(args[...])           →  MCP03: command injection
open(args["path"])                  →  MCP03: path traversal
cursor.execute(args["query"])       →  MCP03: SQL injection
os.environ, config.get("secret")   →  MCP04: secret exposure in response
return {"content": sensitive_data}  →  MCP04: data exposure

# Server configuration
server.run()                        →  MCP06: check if auth middleware exists
StdioServerTransport               →  local — lower risk
SSEServerTransport / StreamableHTTPServerTransport  →  network — check auth
```

```typescript
// Node MCP SDK patterns
server.tool("name", schema, handler)  →  find all tool definitions
server.resource("uri", handler)       →  find all resource definitions

// Same injection checks in handlers
exec(args.command)                    →  MCP03
fs.readFile(args.path)                →  MCP03
```
