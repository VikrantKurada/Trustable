# PRD: Trustable – LLM Quality & Governance Overlay

## 1. Executive Summary
**Trustable** is a modular developer tool designed to overlay onto existing early-stage LLM projects in GitHub. It acts as a configurable middle layer—or set of guardrails—that enforces security, reviewability, testability, auditability, and explainability without requiring a full rewrite of the host application. 

**Core Paradigm:** The tool functions via a configuration-as-code approach (e.g., a `trustable.yaml` file) dropped into the root of a GitHub repository, accompanied by a lightweight SDK/CLI and optionally a VS Code extension for inline developer feedback.

## 2. Architectural Principles
To ensure adoption, the system must adhere strictly to these principles:
1.  **Opt-In (Optional):** Developers can enable individual modules (e.g., just Auditability) without activating the whole suite. If Trustable fails, the core LLM application must fail-open or fallback gracefully.
2.  **Configurable:** All thresholds, metrics, and data routing must be defined in declarative YAML/JSON files, abstracting the complexity from the application code.
3.  **Extendable:** Built on plugin architectures. Teams must be able to write custom Python scripts, utilize workflow automation like n8n for automated alerting, or use local orchestration endpoints (like an Ollama container) to define their own evaluation logic or security scanners.
4.  **Local-First Capable:** Must support execution on local developer workstations via Docker. The architecture optimizes for high-end local development environments (e.g., leveraging RTX 5090 GPUs and 64GB of RAM) to run comprehensive evaluation models before pushing to CI/CD pipelines.

---

## 3. Core Feature Modules

### 3.1. Reviewability Module: Prompts-as-Code
**Goal:** Make non-deterministic prompt changes reviewable in standard GitHub PR workflows.

| Feature | Description | Acceptance Criteria |
| :--- | :--- | :--- |
| **Prompt Registry** | Forces separation of prompts from business logic into version-controlled files. | SDK provides a `load_prompt(id, version)` function. |
| **Semantic Diffing** | GitHub Action that comments on PRs showing exact text changes to prompts. | Action successfully posts PR comments highlighting added/removed tokens in template files. |

### 3.2. Testability Module: Pluggable Evaluation
**Goal:** Provide a test harness for semantic outputs rather than strict string matching.

| Feature | Description | Acceptance Criteria |
| :--- | :--- | :--- |
| **Golden Dataset Runner** | Executes a designated set of inputs against the LLM on every commit. | CLI command `trustable test` runs configured dataset and outputs a pass/fail matrix. |
| **LLM-as-a-Judge API** | Allows developers to configure a secondary model to score the primary model's outputs. | Supports routing eval queries to local endpoints (e.g., `localhost:11434` for Ollama) or remote APIs. |
| **Custom Assertions** | YAML-defined rules (e.g., "Response must be < 500 tokens", "Response must contain valid JSON"). | Test suite fails the CI build if assertions are breached. |

### 3.3. Auditability Module: Telemetry & Log Structuring
**Goal:** Create an immutable, structured trace of every LLM interaction for production debugging and enterprise governance.

| Feature | Description | Acceptance Criteria |
| :--- | :--- | :--- |
| **OpenTelemetry Wrappers** | Auto-instruments popular LLM libraries (LangChain, OpenAI, LiteLLM) to capture latency, tokens, and raw payloads. | Decorator `@trustable.trace` captures full request/response lifecycle. |
| **Medallion-Structured Sinks** | Organizes audit logs into a tiered structure (Bronze: Raw Traces, Silver: Cleaned, Gold: Aggregated) ready for enterprise platforms. | Config supports routing directly to platforms like Azure Databricks and applying Unity Catalog governance policies. |

### 3.4. Security Module: Injection & Leakage Guards
**Goal:** Intercept and sanitize inputs and outputs dynamically.

| Feature | Description | Acceptance Criteria |
| :--- | :--- | :--- |
| **PII/Secret Masking** | Regex and NLP-based scanning to redact sensitive data before it hits the LLM API. | Configurable `mask_entities` array (e.g., `[EMAIL, CREDIT_CARD]`). |
| **Injection Scanning** | Evaluates user input against a known database of prompt injection heuristics before execution. | High-risk prompts return an immediate `400 Bad Request` without hitting the LLM. |

### 3.5. Explainability Module: Context Lineage
**Goal:** Provide developers and end-users with the "why" behind an output, especially for RAG workflows.

| Feature | Description | Acceptance Criteria |
| :--- | :--- | :--- |
| **Context Retention Logging** | Maps the exact vector-DB chunks retrieved to the final generated output. | Logs include an array of `source_documents` and their similarity scores. |
| **Reasoning Extraction** | Forces the LLM to output its Chain-of-Thought into a hidden data object before delivering the final user-facing answer. | SDK automatically parses out the `<thinking>` tags into the Silver-tier audit logs. |

---

## 4. Configuration Schema (`trustable.yaml`)
Provide this schema definition to Claude Code as the target configuration format the product must parse.

```yaml
version: "1.0"
project: "my-llm-app"

modules:
  security:
    enabled: true
    pii_masking: ["EMAIL", "API_KEYS"]
    block_injections: true

  audit:
    enabled: true
    sink: "databricks" # Integrated with Unity Catalog
    log_level: "silver" 

  test:
    enabled: true
    evaluator_model: "ollama/llama3" # Configurable endpoint for local execution
    golden_dataset: "./tests/golden_data.json"

  explainability:
    enabled: true
    capture_rag_context: true
```

## 5. Implementation Phases for AI Assistant
When feeding this to your coding assistant, instruct it to build in the following sequence:

1.  **Phase 1: Core CLI & Configuration Parser.** Build the Python CLI application that can ingest `trustable.yaml` and establish the base directory structure.
2.  **Phase 2: SDK Decorators (Audit & Explainability).** Implement the `@trustable.trace` python decorators that developers will wrap around their existing LLM calling functions.
3.  **Phase 3: Testing Harness.** Build the execution engine that runs the `golden_data.json` through the configured evaluator model.
4.  **Phase 4: Integrations & CI/CD.** Wrap the CLI in a Dockerfile optimized for running inside a GitHub Actions workflow, and establish the sink routes to enterprise data platforms.
