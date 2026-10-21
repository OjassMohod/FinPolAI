# MASTER PROMPT — POLICYGUARD AI
## Agentic AI + RAG Banking Policy Compliance Verification System

Act as my senior full-stack engineer, AI systems architect, and technical development partner.

Your objective is to **design, implement, test, and deliver a fully working hackathon prototype** of an AI-powered banking policy compliance verification platform.

Do not stop at planning, scaffolding, writing documentation, or generating a frontend mockup. Build a functional end-to-end application.

You may make reasonable technical decisions independently. Prioritize reliability, functionality, clarity, and ease of demonstration.

---

# 1. PROJECT OVERVIEW

**Project Name:** PolicyGuard AI

**Domain:** Fintech / Banking / Agentic AI

**Target:** Hackathon prototype, potentially for an Airwallex-related fintech challenge.

### Problem Statement

Banks handling international transactions must verify transactions against numerous internal policies, cross-border restrictions, transaction thresholds, identity verification requirements, and documentation requirements.

These policies can be spread across multiple documents, making manual verification time-consuming and difficult to audit.

Traditional rule engines can automatically enforce predefined rules but may struggle with finding relevant information across large collections of unstructured policy documents.

LLMs can interpret documents, but allowing them to independently make compliance decisions introduces reliability and explainability concerns.

### Proposed Solution

Build PolicyGuard AI, an intelligent transaction policy verification assistant combining three components:

**1. Agentic AI**

An LLM-powered agent that coordinates verification, selects tools, retrieves additional information when necessary, and decides which investigative steps to perform.

**2. Retrieval-Augmented Generation (RAG)**

A semantic retrieval system that searches banking policy documents and supplies relevant passages to the agent.

**3. Deterministic Rule Engine**

A Python-based system that evaluates transactions against explicitly defined, machine-readable policy rules.

The LLM must never be the ultimate authority for determining rule compliance.

### Core Principle

**The AI agent investigates, RAG retrieves, and the rule engine evaluates.**

The agent explains the results and recommends next steps.

All assessments are advisory. No real banking transactions are approved, rejected, or executed.

---

# 2. TECHNOLOGY STACK

Use the following technology stack unless a change is necessary for compatibility.

## Frontend

- HTML5
- CSS3
- Vanilla JavaScript
- Fetch API for backend communication

Build a polished, responsive frontend.

Do not use Streamlit.

Avoid React or large frontend frameworks unless there is a compelling reason.

## Backend

- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic for validation

## LLM / Agentic AI

Use an LLM accessed through a configurable **OpenAI-compatible API**.

The integration should support any compatible provider offering tool calling.

Use environment variables:

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

Do not hardcode a particular paid provider or require billing.

I intend to use a free-tier API where possible.

Provide a clearly explained setup process.

Never hardcode or expose API keys.

## RAG System

Implement semantic retrieval using:

- sentence-transformers
- A small, efficient embedding model, such as `all-MiniLM-L6-v2`
- NumPy cosine similarity for vector search

The embedding model should run locally on a typical student laptop.

Use an actual vector-based semantic search implementation, not just keyword matching.

A vector database is not required for this MVP.

Allow locally cached embeddings to be reused.

If the embedding model is unavailable, provide a clearly labeled TF-IDF fallback rather than silently pretending semantic retrieval is active.

## Document Processing

- pypdf for PDF text extraction
- Native Python utilities for TXT and Markdown
- Chunking and metadata extraction

## Rule Engine

- Custom deterministic Python engine
- Machine-readable JSON policies
- Explicit, validated rule conditions
- No LLM-driven compliance calculations

## Database

SQLite for:

- Transaction history
- Verification results
- Policy metadata
- Agent execution traces
- Audit records

The system must run locally without external database infrastructure.

---

# 3. SYSTEM ARCHITECTURE

Implement the following architecture:

```text
             WEB APPLICATION
           HTML / CSS / JavaScript
                    |
                    v
              FASTAPI BACKEND
                    |
                    v
            AGENT ORCHESTRATOR
                    |
          +---------+---------+
          |                   |
          v                   v
     RAG SYSTEM         RULE ENGINE
          |                   |
          v                   v
    Policy Documents    Structured Rules
          |                   |
          +---------+---------+
                    |
                    v
           VERIFICATION REPORT
                    |
                    v
          WEB UI + AUDIT HISTORY
```

The agent must use actual backend tools.

The rule engine must remain independent of the LLM.

The application should remain functional if the LLM API is unavailable.

---

# 4. CORE FEATURE A — TRANSACTION SUBMISSION

Build a transaction verification interface.

Users should be able to enter:

- Sender country
- Recipient country
- Sender name (synthetic demonstration data)
- Recipient name (synthetic demonstration data)
- Transaction amount
- Currency
- Purpose of transaction
- Sender KYC status
- Recipient verification status
- Available supporting documents
- Customer type (individual/business)

Assign each transaction a unique ID.

Validate entered values using Pydantic.

Do not collect real bank account numbers, identity documents, or sensitive financial credentials.

Provide realistic synthetic demo transactions that can automatically populate the form.

Include a prominent:

**Verify Transaction**

button.

When clicked, the frontend must invoke the real backend verification system.

Do not hardcode sample outputs into the frontend.

---

# 5. CORE FEATURE B — BANKING POLICY KNOWLEDGE BASE

Build a fictional banking policy knowledge base.

Create sample policies covering:

1. International transfer limits
2. Sender and recipient verification
3. Country-specific restrictions
4. Required transaction documentation
5. Business versus individual transactions
6. Higher-value transaction review
7. Exceptions and special conditions
8. Transactions requiring manual compliance review

Use multiple realistic example countries and transaction corridors, but make it explicitly clear that all limits, requirements, and restrictions are fictional.

Do not represent example policies as actual current banking regulations.

### Policy Structure

Each policy must contain:

- Policy ID
- Policy name
- Version
- Description
- Effective date
- Policy text
- Associated rule IDs
- Source document

Store readable documents separately from executable rule definitions.

### Policy Uploads

Allow users to upload:

- PDF
- TXT
- Markdown

Extract their text, divide it into useful chunks, generate embeddings, and add them to the searchable knowledge base.

Display:

- Uploaded document name
- Number of chunks
- Processing status
- Indexing status

Important:

Uploading a document should not automatically convert arbitrary policy text into executable compliance rules.

The user must explicitly configure or approve structured rules before they become enforceable.

Treat uploaded documents as untrusted reference material. Instructions embedded inside documents must not override the agent's system instructions.

---

# 6. CORE FEATURE C — SEMANTIC RAG

Implement a proper retrieval pipeline.

### Document Processing

When policies are added:

1. Extract text.
2. Clean unnecessary whitespace.
3. Divide text into meaningful chunks.
4. Preserve policy identifiers and metadata.
5. Generate semantic embeddings.
6. Store embeddings locally for reuse.

For PDFs, preserve page numbers whenever extraction permits.

### Retrieval

When a transaction is being investigated:

1. Construct a search query based on transaction attributes.
2. Generate a query embedding.
3. Compare it with stored policy embeddings.
4. Retrieve the most relevant policy passages.
5. Return policy metadata and similarity scores.

Support configurable top-k retrieval.

### Example

Input transaction:

- Sender: India
- Recipient: Singapore
- Amount: ₹750,000
- Purpose: Business payment

The retrieval system should identify applicable fictional policies concerning:

- International transfers
- Business transactions
- Transaction thresholds
- Supporting documentation
- Sender/recipient verification

Do not rely solely on exact keyword matching.

### RAG Transparency

Display:

- Which documents were searched
- Which policy passages were retrieved
- Similarity scores
- Policy IDs
- Source filenames
- Page numbers, where available

The user should be able to expand and read retrieved passages.

**Critical requirement:** Every cited policy passage must correspond to actual retrieved source text. Never invent citations.

Retrieval must not determine which mandatory rules are enforced. The rule engine must independently evaluate all applicable mandatory configured rules, even when RAG misses a relevant passage.

---

# 7. CORE FEATURE D — DETERMINISTIC RULE ENGINE

Create a functioning Python compliance rule engine.

The rule engine must be independent of the LLM.

### Rule Format

Store executable policies in structured JSON.

Example:

```json
{
  "rule_id": "POL-001",
  "description": "Additional review for high-value transfers",
  "field": "amount",
  "operator": "greater_than",
  "value": 500000,
  "currency": "INR",
  "action": "manual_review",
  "policy_reference": "POLICY-TRANSFER-01"
}
```

This threshold is fictional.

### Supported Rule Types

Include:

- Greater-than / less-than comparisons
- Equality / inequality
- Country inclusion and exclusion
- Boolean verification requirements
- Required document checks
- Transaction-purpose checks
- Conditional rules
- Explicit exceptions

Implement a safe, declarative rule evaluator.

Do not use Python `eval()` or execute arbitrary expressions from JSON.

Ensure amount thresholds use consistent currencies. Do not compare numerical amounts from different currencies without an explicitly configured conversion method and rate source.

For the MVP, prefer fictional limits defined separately for supported currencies rather than introducing live exchange-rate dependencies.

### Rule Evaluation

For each applicable rule, return:

- Rule ID
- Policy reference
- Rule description
- Actual value
- Expected condition
- Result
- Explanation

Supported outcomes:

**PASS:** All mandatory checks pass.

**FLAGGED:** At least one configured violation is detected.

**NEEDS INFORMATION:** Essential transaction information is missing.

**REVIEW REQUIRED:** No configured violation has been established, but a rule requires manual review.

Define a consistent precedence when multiple conditions occur. Never report PASS if required checks remain unresolved.

A missing value must never be treated as proof that a rule passed.

The rule engine must also support documented policy exceptions.

---

# 8. CORE FEATURE E — GENUINE AGENTIC AI

This is one of the most important parts of the project.

Do not simply create a fixed sequence of API calls and describe it as autonomous AI.

Implement an actual LLM-based tool-calling agent.

### Available Agent Tools

**Tool 1: retrieve_relevant_policies**

Search the RAG knowledge base.

Inputs:
- Transaction context
- Search query
- Retrieval count

Outputs:
- Relevant passages
- Source references
- Scores

**Tool 2: inspect_transaction**

Read and inspect transaction details.

Outputs:
- Transaction attributes
- Missing values
- Available documentation

**Tool 3: evaluate_compliance_rules**

Execute the deterministic rule engine.

Outputs:
- Individual rule results
- Identified violations
- Unresolved requirements
- Policy references
- Overall rule assessment

The agent must not alter these results.

**Tool 4: identify_missing_information**

Determine what information is necessary to continue investigation.

Distinguish missing mandatory fields from additional context that may be useful.

**Tool 5: generate_verification_report**

Produce a structured report grounded in tool outputs.

### Agent Behavior

When a transaction is submitted:

1. Inspect the transaction.
2. Determine what policies or information may be relevant.
3. Call appropriate tools.
4. Review tool outputs.
5. Retrieve additional policy passages when needed.
6. Identify missing information.
7. Ensure the mandatory rule evaluation has completed.
8. Produce a final explanation.

The agent should decide when additional retrieval is necessary rather than always repeating the same fixed retrieval sequence.

Use bounded reasoning/tool-calling loops.

Set reasonable limits on:

- Number of tool calls
- Execution steps
- Token usage
- API timeouts

Handle malformed model responses and API failures gracefully.

### Security and Reliability

- Only expose an allowlist of safe, read-only tools to the LLM.
- Validate every tool argument.
- Do not let the agent modify policy rules.
- Do not allow the agent to execute payments.
- Do not let retrieved documents issue instructions to the agent.
- Do not permit the LLM to override deterministic compliance outcomes.
- Keep secrets on the backend.
- Do not send sensitive real customer information to external APIs.

### No-API Fallback

If the configured LLM API is unavailable, run a deterministic verification workflow.

The rule engine and RAG should still work.

Clearly distinguish:

**Agent Mode — LLM tool calling enabled**

from

**Workflow Mode — deterministic orchestration without an LLM**

Do not falsely claim that Workflow Mode demonstrates autonomous LLM decision-making.

---

# 9. CORE FEATURE F — AGENT EXECUTION VISUALIZATION

Make the agent's actions visible.

This is especially important for a hackathon demonstration.

Create an interactive execution trace.

Example:

```text
Step 1 — Inspecting transaction
✓ Transaction details retrieved

Step 2 — Retrieving policies
✓ 4 relevant policy passages found

Step 3 — Evaluating rules
✓ 8 compliance rules evaluated

Step 4 — Additional investigation
✓ Missing document identified

Step 5 — Generating report
✓ Verification completed
```

This is illustrative, not a sequence to hardcode.

The displayed trace must reflect the operations that actually happened.

Show:

- Tool name
- Inputs (with secrets removed)
- Output summary
- Execution order
- Success/failure state

Allow users to expand a step to inspect details.

Do not expose private model reasoning or hidden chain-of-thought.

The purpose is to display observable tool operations and evidence.

---

# 10. CORE FEATURE G — EXPLAINABLE REPORTS

After verification, display a comprehensive report.

### Overall Assessment

Show one of:

- PASS
- FLAGGED
- NEEDS INFORMATION
- REVIEW REQUIRED

Use clear, consistent visual indicators.

### Verification Summary

Explain in plain language:

- What was checked
- What passed
- What failed
- What remains uncertain
- What the user should do next

### Rule Evaluation Table

Columns:

| Rule | Actual Value | Requirement | Result | Policy Reference |
|---|---|---|---|---|

### Retrieved Evidence

Display relevant policy passages with citations.

### Recommended Next Steps

Examples:

- Provide a missing document
- Complete verification
- Request manual compliance review
- Supply additional transaction information

Recommendations must be grounded in actual rule results.

### Explanation Generation

When an LLM is available, use it to generate clear, understandable explanations.

But:

- Never invent policy requirements.
- Never invent citations.
- Never change rule outcomes.
- Clearly identify unresolved questions.

When no LLM is available, use deterministic explanation templates.

---

# 11. CORE FEATURE H — AUDIT HISTORY

Save verification records using SQLite.

Store:

- Transaction ID
- Timestamp
- Transaction details (synthetic demo data)
- Applicable policy versions
- Rule evaluation results
- Final assessment
- Retrieved references
- Agent tool execution trace
- Execution mode

Create an Audit History page.

Allow users to:

- View previous transactions
- Filter by assessment
- Inspect past verification reports
- Review the agent's recorded actions

Use database migrations or reliable initialization logic.

Do not overwrite past assessments when policies change.

---

# 12. FRONTEND DESIGN REQUIREMENTS

Build a modern fintech-style interface using HTML, CSS, and JavaScript.

The application should feel like a real financial technology product rather than a basic university assignment.

### Design Direction

- Clean, professional appearance
- Light theme with dark navy accents
- Clear typography
- Consistent spacing
- Responsive layout
- Minimal unnecessary animations
- Good visual hierarchy

Prioritize readability over decoration.

### Main Pages

**Page 1: Dashboard**

Include:

- Overview statistics from stored demo records
- Transaction form
- Sample transaction selector
- Verification button
- Current verification status
- Final assessment

**Page 2: Verification Details**

Include:

- Overall decision
- Rule evaluation table
- Retrieved policy evidence
- Expandable agent execution timeline
- Missing information
- Recommended next steps

**Page 3: Policy Knowledge Base**

Include:

- List of policies
- Search functionality
- Upload interface
- Policy details
- Source documents
- Structured rule definitions

**Page 4: Audit History**

Include:

- Past verifications
- Assessment filters
- Transaction details
- Previous reports

### Frontend Behavior

Use actual API calls to the FastAPI backend.

Do not use fake loading animations that are disconnected from real backend operations.

Show meaningful loading states.

Handle API errors.

Make navigation intuitive.

For long agent operations, use polling or server-sent events to display genuine progress when practical.

---

# 13. DEMONSTRATION TRANSACTIONS

Create at least eight synthetic transactions with different expected outcomes.

Include:

1. A fully compliant transaction.
2. A transaction exceeding a fictional threshold.
3. A transaction missing required supporting documents.
4. A transaction involving an unsupported corridor.
5. A transaction with incomplete identity verification.
6. A high-value transaction requiring manual review.
7. A transaction with insufficient information.
8. A transaction eligible for an explicitly defined policy exception.

All expected results must derive from the actual configured rules.

Do not hardcode the final outcomes.

Include at least one additional scenario where multiple policy conditions apply simultaneously.

Ensure policy exceptions are evaluated correctly.

Clearly label the entire dataset as fictional.

---

# 14. API ENDPOINTS

Create a logical FastAPI API structure.

Suggested endpoints:

```text
GET    /api/health

POST   /api/transactions/verify

GET    /api/transactions/samples

GET    /api/verifications

GET    /api/verifications/{id}

GET    /api/policies

GET    /api/policies/{id}

POST   /api/policies/upload

POST   /api/policies/search

GET    /api/system/status
```

Adjust endpoint naming if required.

Use documented Pydantic request/response schemas.

Expose FastAPI's interactive documentation.

Ensure frontend and backend integration works correctly.

The system status endpoint should report whether LLM mode, embeddings, and the database are operational.

---

# 15. TESTING REQUIREMENTS

Write automated tests using pytest.

### Test Rule Engine

Verify:

- Threshold comparisons
- Missing fields
- Country restrictions
- Required documentation
- Multiple simultaneous violations
- Explicit policy exceptions
- Boundary values
- Currency handling

### Test RAG

Verify:

- Documents can be indexed
- Queries return relevant passages
- Source references are preserved
- PDF extraction works for text-based PDFs
- Missing or unreadable documents are handled gracefully

### Test Agent

Verify:

- Tool arguments are validated
- Tool calls execute real functions
- Unsupported tools are rejected
- Failures are handled appropriately
- Mandatory compliance checks are not skipped
- LLM explanations cannot alter rule assessments
- Workflow fallback works without API keys

Mock LLM responses for automated testing.

Do not require paid API access to run tests.

### Test API

Verify:

- Endpoints return expected schemas
- Valid transaction requests succeed
- Invalid requests return useful errors
- History persists correctly
- Sample transactions work end to end

### Manual Testing

Test the application through actual API requests.

Confirm that sample transactions produce expected results.

Do not mark features complete without successful tests.

---

# 16. PROJECT STRUCTURE

Organize the project into understandable modules.

Suggested structure:

```text
policyguard-ai/
│
├── frontend/
│   ├── index.html
│   ├── css/
│   └── js/
│
├── backend/
│   ├── main.py
│   ├── api/
│   ├── agents/
│   ├── rag/
│   ├── rules/
│   ├── database/
│   ├── models/
│   └── services/
│
├── data/
│   ├── policies/
│   ├── rules/
│   ├── sample_transactions/
│   └── uploads/
│
├── tests/
│
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── prompt.md
```

You may adjust the structure to improve maintainability.

Keep the code modular but avoid unnecessary abstraction.

---

# 17. DEVELOPMENT PROCESS

Work incrementally and validate every major component.

## Phase 1 — Foundation

- Create project structure.
- Initialize FastAPI.
- Set up SQLite.
- Create sample policies and transactions.
- Establish environment configuration.

## Phase 2 — Rule Engine

- Implement JSON-based rules.
- Build evaluation logic.
- Handle exceptions and missing information.
- Write tests.
- Verify expected outcomes.

## Phase 3 — RAG

- Implement text extraction.
- Implement document chunking.
- Generate local embeddings.
- Implement similarity search.
- Preserve citations and metadata.
- Test relevant policy retrieval.

## Phase 4 — Agentic AI

- Implement the LLM client.
- Define tools and schemas.
- Build the tool-calling loop.
- Integrate RAG and rule engine.
- Implement bounded execution.
- Implement deterministic fallback.
- Test orchestration.

## Phase 5 — Frontend

- Build all required pages.
- Connect API endpoints.
- Build transaction verification workflow.
- Visualize agent actions.
- Display results and citations.

## Phase 6 — Integration

- Test frontend/backend communication.
- Test transaction verification.
- Test policy uploads.
- Test history and persistence.
- Fix bugs.

## Phase 7 — Final Validation

- Run automated tests.
- Launch the full application.
- Verify example scenarios.
- Check error handling.
- Review UI usability.
- Update documentation.

Do not repeatedly ask for approval between phases unless absolutely necessary.

---

# 18. COST AND PERFORMANCE CONSTRAINTS

The prototype should be usable without paid infrastructure.

Prefer:

- Free-tier LLM APIs
- Local semantic embeddings
- SQLite
- Local FastAPI hosting
- Open-source dependencies

Avoid unnecessary paid services.

Make API usage efficient.

Do not send entire policy documents to the LLM unnecessarily.

Use RAG to supply relevant policy chunks.

Limit repeated retrieval and model calls.

Cache embeddings.

Keep model selection configurable.

Explain any first-run model download requirements.

If an API provider does not support tool calling, explain the limitation and use Workflow Mode rather than falsely claiming the model is acting autonomously.

---

# 19. IMPORTANT DESIGN PRINCIPLES

Follow these principles throughout development.

**Principle 1: Working functionality over visual appearance.**

Build the functioning backend first.

**Principle 2: Actual Agentic AI.**

The LLM should genuinely select and invoke tools when Agent Mode is enabled.

**Principle 3: Deterministic compliance evaluation.**

LLM outputs must not determine the official rule results.

**Principle 4: Evidence-based explanations.**

Every reported violation must be traceable to a configured rule and policy reference.

**Principle 5: Transparency.**

Users should understand what the system checked and why.

**Principle 6: Clear demo boundaries.**

Use only synthetic transactions and fictional policies.

**Principle 7: Graceful failure.**

The application must remain usable when an API request fails.

**Principle 8: Easy extensibility.**

Keep components modular so the application could later integrate actual banking APIs and enterprise policy systems.

---

# 20. FUTURE EXPANSION

Design interfaces that would make these integrations possible in future:

- Airwallex sandbox APIs
- Realistic transaction event ingestion
- Human approval workflows
- More advanced vector databases
- Policy version comparisons
- Multiple specialized agents
- Compliance officer dashboards
- Policy updates and change detection

Do not implement these integrations now unless essential.

Avoid scope creep.

---

# 21. DOCUMENTATION AND HANDOFF

Create a detailed README containing:

1. Project overview.
2. Architecture explanation.
3. Technology stack.
4. Installation steps.
5. Environment variable setup.
6. How to configure a free-tier compatible LLM API.
7. How to launch the backend.
8. How to launch the frontend.
9. How to use demo transactions.
10. How RAG works.
11. How the rule engine works.
12. How the AI agent uses tools.
13. How to run tests.
14. Known limitations.
15. Potential future improvements.

Also create `prompt.md` documenting the project requirements and major implementation decisions for the hackathon.

Provide exact terminal commands for starting the application.

Explain how to configure a new LLM model without rewriting the agent.

---

# 22. ACCEPTANCE CRITERIA

Consider the project complete only when:

- The frontend loads successfully.
- The backend starts successfully.
- Sample transactions populate the form.
- Verification invokes the real backend.
- Semantic RAG retrieves policy passages.
- The rule engine evaluates configured rules.
- Agent Mode makes genuine LLM tool calls when supported and configured.
- Workflow Mode works without an API key.
- Compliance results contain legitimate policy references.
- The UI displays actual execution traces.
- Audit history persists.
- Policy documents can be uploaded and indexed.
- Automated tests pass.
- The README contains working installation instructions.

If something cannot be completed, explicitly identify the incomplete functionality instead of pretending it works.

---

# 23. FINAL INSTRUCTIONS

Start implementing this project immediately.

Do not respond with only a plan.

Create the files, implement the modules, install necessary dependencies where supported, run tests, and fix issues.

Make reasonable engineering decisions autonomously.

Prioritize delivering a fully functioning MVP over implementing unnecessary advanced functionality.

After completion, provide:

**A.** Summary of implemented functionality.

**B.** Project architecture.

**C.** Exact steps to launch the application.

**D.** How to configure the free-tier LLM API.

**E.** Test results, distinguishing executed tests from unverified functionality.

**F.** A walkthrough of three example transactions.

**G.** Known limitations and possible improvements.

Remember:

**The AI agent investigates. RAG retrieves. The rule engine evaluates. The system explains.**

Build a real demonstration of all four.
---

# Implementation decisions

- The existing FinPolAI checkout is the project root. One FastAPI process serves both API and vanilla JS frontend, avoiding CORS and separate frontend build dependencies.
- Eight fictional policy documents map to 37 structured rules. All configured rules are considered on every assessment; retrieval has no control over enforcement.
- Amounts use Decimal and five separate currency schedules, never implicit currency conversion.
- Missing facts use three-valued logic. Precedence: FLAGGED > NEEDS INFORMATION > REVIEW REQUIRED > PASS. Empty supporting-document lists are known absence; null is unknown.
- Scholarship exceptions waive only the source-of-funds requirement. Uploaded reference material never creates enforceable rules.
- Local MiniLM sentence-transformer vectors are L2 normalized; NumPy dot product computes cosine similarity. Cached .npy vectors use allow_pickle=False. If downloading or encoding fails, status explicitly changes to TF-IDF fallback.
- LLM configuration is optional. A bounded OpenAI-compatible tool-calling loop selects actual read-only functions. Mandatory safeguards finish every rule assessment. Responses that do not call tools use Workflow Mode.
- To prevent invented claims, the LLM selects validated rule/citation identifiers and an assessment-compatible overview; the server renders explanation text from authoritative tool outputs. Free-form model prose is not displayed.
- SQLite stores complete immutable JSON report snapshots, including evidence excerpts, condition definitions, policy versions and execution traces. Uploaded text/chunks persist in SQLite. Raw files are processed in memory and not retained.
- Upload limits: 5 MiB, 80 PDF pages, 300,000 extracted characters; scanned PDFs need external OCR.
- No authentication, real banking API integration, payment execution, live FX rates, or automatic text-to-rule activation. Local synthetic demonstration only.
- Required verification and readiness commands, provider configuration and remaining external-access limitations are in README.md and VALIDATION.md.
