# Developer Memory Abstraction Layer Architecture

## Overview

The Developer Memory Abstraction Layer integrates **TencentDB Agent Memory (MemoryCore)** into the development workflow while maintaining strict provider independence and zero-coupling.

---

## Key Architecture Principles

1. **Provider-Agnostic Interface (`BaseMemoryProvider`):**  
   The application interacts exclusively with `MemoryService` and the `BaseMemoryProvider` abstract interface defined in `etsy_pipeline.memory.base`.

2. **HTTP Service Isolation:**  
   `TencentDBMemoryProvider` connects to MemoryCore Gateway over HTTP (`http://127.0.0.1:8420`) using `httpx`. The application does not import or depend on TencentDB source code.

3. **High-Signal Noise Filtering (`MemoryFilter`):**  
   Before any text is stored in memory, `MemoryFilter` rejects stack traces, installation outputs, terminal dumps, and short/transient text.

4. **Coexistence with `AGENTS.md`:**  
   - `AGENTS.md`: Immutable repository rules and static standards (priority 1).
   - `MemoryCore`: Dynamic, contextually retrieved past engineering memories & bug fixes (priority 2).
   - Combined prompt structure: `AGENTS.md -> Relevant Memory -> User Request -> LLM`.

5. **Non-Blocking Graceful Fallback:**  
   Calls enforce a 1.5-second HTTP timeout and a 3-strikes circuit breaker (60-second cooldown). If MemoryCore is offline, all calls degrade silently without throwing exceptions or blocking developer tasks.

---

## Directory Layout

```
etsy_pipeline/memory/
├── __init__.py                # Package exports
├── base.py                    # BaseMemoryProvider ABC & MemoryEntry model
├── filter.py                  # High-signal noise filter
├── tencent_provider.py        # TencentDB HTTP client & Mock provider
└── service.py                 # Main MemoryService facade & prompt formatter
```

---

## Configuration (`Settings`)

- `memory_enabled`: Feature flag (default `False`).
- `memory_provider`: Backend provider (`"tencentdb"`, `"mock"`).
- `memory_gateway_url`: Base URL of MemoryCore Gateway (`"http://127.0.0.1:8420"`).
- `memory_api_key`: Optional Bearer token.
- `memory_namespace_dev`: Namespace string (`"craftdesk-dev"`).
- `memory_timeout_sec`: Request timeout in seconds (`1.5`).
- `memory_server_dir`: Absolute path to your cloned `TencentDB-Agent-Memory` directory.

---

## Node.js Background Auto-Start

The Memory Abstraction Layer implements an automated Node.js process spawner. 

When `MemoryService` initializes or queries the provider, it runs a quick async health check. If the MemoryCore Gateway is unreachable:
1. It locates the local `TencentDB-Agent-Memory` repository at `memory_server_dir`.
2. It verifies if `node_modules` exists; if not, it automatically runs `npm install` in the background.
3. It spawns the Node.js standalone gateway (`node --import tsx src/gateway/server.ts`) in a detached, hidden background process (using `subprocess.CREATE_NO_WINDOW` on Windows).
4. The service waits 2 seconds for initialization to complete and continues operations seamlessly with zero developer intervention.

---

## CLI Management Tool

Interact with developer memory via CLI:
```bash
# Health check
python scripts/memory_cli.py health

# Capture memory
python scripts/memory_cli.py capture "Workers in etsy_pipeline must be stateless" --category architecture

# Recall memory
python scripts/memory_cli.py recall "stateless"
```
