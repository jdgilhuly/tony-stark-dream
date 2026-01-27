# JARVIS Agent Routing System - Technical Plan

## Project Overview

This project adds intelligent agent routing capabilities to JARVIS (tony-stark-dream), enabling the AI assistant to automatically detect user intent and route requests to specialized agents from the claude_agents collection. JARVIS will seamlessly introduce domain specialists (e.g., "Allow me to consult our Python specialist...") while maintaining its core butler personality for general interactions.

The system will integrate all 140 agent definitions from claude_agents, using LLM-based intent classification to select the most appropriate specialist. For multi-domain requests, agents will be consulted sequentially with synthesized responses. Session-based caching ensures conversational continuity, and users can explicitly request specific agents via natural voice/text commands.

---

## Functional Requirements

### Core Agent Routing

- **FR-1:** System SHALL automatically classify user intent and route to the most appropriate agent from 140 available specialists
- **FR-2:** System SHALL support seamless handoff introductions (e.g., "Allow me to consult our security specialist...")
- **FR-3:** System SHALL maintain session-based agent caching - follow-up questions stay with the current specialist until topic changes
- **FR-4:** System SHALL fall back to default JARVIS personality when no specific agent is a clear match
- **FR-5:** System SHALL support explicit agent requests via natural language (e.g., "ask the Python expert", "consult the DevOps engineer")

### Multi-Agent Handling

- **FR-6:** System SHALL detect when requests span multiple agent domains
- **FR-7:** System SHALL sequentially consult multiple agents for cross-domain requests
- **FR-8:** System SHALL synthesize responses from multiple agents into a coherent reply

### Agent Management

- **FR-9:** System SHALL load agent definitions from local markdown files at startup
- **FR-10:** System SHALL parse agent metadata (name, description, expertise areas, tools) from frontmatter
- **FR-11:** System SHALL maintain an agent registry with searchable capabilities
- **FR-12:** System SHALL support hot-reloading of agent definitions without service restart

### User Interaction

- **FR-13:** System SHALL allow users to ask "what specialists are available?" and receive a categorized list
- **FR-14:** System SHALL allow users to ask about specific agent capabilities
- **FR-15:** System SHALL indicate which specialist is currently active in response metadata

---

## Non-Functional Requirements

### Performance

- **NFR-1:** Intent classification SHALL complete in < 500ms (p95) using a lightweight LLM call
- **NFR-2:** Agent definition loading SHALL complete in < 2 seconds at startup for all 140 agents
- **NFR-3:** Agent routing overhead SHALL add < 1 second to total response time
- **NFR-4:** Session cache lookups SHALL complete in < 10ms

### Scalability

- **NFR-5:** System SHALL support up to 500 agent definitions without architectural changes
- **NFR-6:** System SHALL handle concurrent classification requests efficiently
- **NFR-7:** Agent registry SHALL use efficient indexing for capability searches

### Reliability

- **NFR-8:** Classification failures SHALL gracefully fall back to default JARVIS mode
- **NFR-9:** Malformed agent files SHALL be logged and skipped without crashing the service
- **NFR-10:** Session cache failures SHALL not block request processing

### Maintainability

- **NFR-11:** Adding new agents SHALL require only adding a markdown file (no code changes)
- **NFR-12:** Agent definitions SHALL follow the existing claude_agents format specification
- **NFR-13:** Routing logic SHALL be configurable via environment variables

### Security

- **NFR-14:** Agent file paths SHALL be validated to prevent directory traversal
- **NFR-15:** User-requested agent names SHALL be sanitized before lookup

---

## Technical Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        JARVIS Clients                                │
│                   (CLI / Mobile / Voice)                             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      API Gateway (:3000)                             │
│                 (Existing - No Changes)                              │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 Conversation Service (:8001)                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    NEW: Agent Router                         │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │    │
│  │  │Intent        │  │Agent         │  │Session       │       │    │
│  │  │Classifier    │──│Registry      │──│Cache         │       │    │
│  │  │(LLM-based)   │  │(140 agents)  │  │(Redis)       │       │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘       │    │
│  │           │                │                                 │    │
│  │           ▼                ▼                                 │    │
│  │  ┌─────────────────────────────────────────────────────┐    │    │
│  │  │              Prompt Composer                         │    │    │
│  │  │  (Merges JARVIS personality + Agent expertise)      │    │    │
│  │  └─────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              Existing: Bedrock/OpenAI Client                │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### New Components

#### 1. Agent Registry (`/src/agents/registry.py`)
- Loads and parses all agent markdown files from `/agents/` directory
- Maintains in-memory index of agent capabilities and metadata
- Provides search methods: `get_by_name()`, `search_by_capability()`, `get_all_categories()`
- Supports hot-reload via file watcher

#### 2. Intent Classifier (`/src/agents/classifier.py`)
- Uses lightweight LLM call (Haiku or similar) for fast classification
- Input: User message + conversation context
- Output: `{ agent_id, confidence, reasoning, is_multi_domain, secondary_agents }`
- Handles explicit agent requests (pattern matching + LLM fallback)

#### 3. Session Cache (`/src/agents/session_cache.py`)
- Redis-backed session state for agent routing
- Stores: `{ session_id: { current_agent, topic_context, message_count } }`
- TTL-based expiration aligned with conversation sessions
- Detects topic changes to trigger re-classification

#### 4. Prompt Composer (`/src/agents/prompt_composer.py`)
- Merges base JARVIS personality with selected agent expertise
- Generates handoff introduction text
- Handles multi-agent response synthesis
- Maintains response format consistency

### Directory Structure Changes

```
services/conversation-service/
├── src/
│   ├── agents/                    # NEW: Agent routing module
│   │   ├── __init__.py
│   │   ├── registry.py            # Agent loading and indexing
│   │   ├── classifier.py          # Intent classification
│   │   ├── session_cache.py       # Session state management
│   │   ├── prompt_composer.py     # Prompt generation
│   │   └── models.py              # Agent data models
│   ├── main.py                    # Modified: Add routing hooks
│   ├── prompts.py                 # Modified: Add agent prompt templates
│   └── ...
├── agents/                        # NEW: Agent definitions (copied from claude_agents)
│   ├── 01-core-development/
│   ├── 02-language-specialists/
│   ├── ...
│   └── 10-research-analysis/
└── ...
```

### Technology Choices

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Intent Classification | Claude Haiku via Bedrock | Fast, cost-effective, consistent with existing stack |
| Session Cache | Redis (existing) | Already deployed, low latency |
| Agent Storage | Local filesystem | Simple, easy to update, no additional infrastructure |
| File Watching | watchdog library | Mature Python library for hot-reload |
| Agent Parsing | python-frontmatter | Standard library for YAML frontmatter parsing |

---

## User Flows

### Flow 1: Automatic Agent Routing (Happy Path)

```
1. User sends message: "How do I optimize this Python function for performance?"
2. Conversation Service receives request
3. Session Cache checked - no existing agent context for this session
4. Intent Classifier invoked:
   - Sends user message to Haiku with agent descriptions
   - Returns: { agent_id: "python-pro", confidence: 0.92 }
5. Agent Registry retrieves full python-pro definition
6. Prompt Composer generates combined prompt:
   - JARVIS base personality
   - Handoff: "Allow me to consult our Python specialist..."
   - Python-pro expertise and guidelines
7. LLM generates response with Python expertise
8. Session Cache updated: { current_agent: "python-pro", topic: "python-optimization" }
9. Response returned with metadata: { agent_used: "python-pro" }
```

### Flow 2: Session Continuity (Follow-up Question)

```
1. User sends follow-up: "What about using multiprocessing?"
2. Session Cache checked - finds { current_agent: "python-pro" }
3. Topic similarity check confirms same domain
4. Skip re-classification, use cached agent
5. Prompt Composer uses python-pro (no handoff intro this time)
6. Response generated with continued Python expertise
```

### Flow 3: Explicit Agent Request

```
1. User says: "Ask the security expert about this code"
2. Intent Classifier detects explicit agent request pattern
3. Pattern matching identifies "security" → potential matches:
   - security-engineer, security-auditor, penetration-tester
4. LLM disambiguates based on context → security-auditor
5. Session Cache updated with new agent
6. Handoff: "Of course. Allow me to consult our security specialist..."
7. Response generated with security-auditor expertise
```

### Flow 4: Multi-Domain Request

```
1. User asks: "Help me build a secure REST API in Python"
2. Intent Classifier detects multi-domain:
   - Primary: api-designer (confidence: 0.85)
   - Secondary: python-pro (confidence: 0.78), security-engineer (confidence: 0.72)
3. Sequential consultation:
   a. API Designer: endpoint structure, REST best practices
   b. Python Pro: implementation details, framework choice
   c. Security Engineer: authentication, input validation
4. Prompt Composer synthesizes responses
5. Handoff: "This spans several areas of expertise. Allow me to consult our specialists..."
6. Combined response with attributed sections
```

### Flow 5: Fallback to Default JARVIS

```
1. User asks: "What's the weather like today?"
2. Intent Classifier runs - no agent match (confidence < threshold)
3. Request routed to existing weather service integration
4. Default JARVIS personality responds
5. No agent cached (standard JARVIS mode)
```

### Flow 6: Topic Change Detection

```
1. User was discussing Python (python-pro cached)
2. User asks: "Now help me set up Kubernetes deployment"
3. Session Cache checked - python-pro active
4. Topic similarity check detects domain change (Python → Infrastructure)
5. Re-classification triggered → kubernetes-specialist selected
6. Session Cache updated with new agent
7. Handoff: "Certainly. Allow me to bring in our Kubernetes specialist..."
```

---

## Data Model

### Agent Definition (Parsed from Markdown)

```python
@dataclass
class AgentDefinition:
    id: str                      # e.g., "python-pro"
    name: str                    # e.g., "Python Pro"
    description: str             # Short description from frontmatter
    category: str                # e.g., "02-language-specialists"
    tools: List[str]             # e.g., ["Read", "Write", "Edit", "Bash"]
    expertise_areas: List[str]   # Extracted from content
    keywords: List[str]          # Auto-generated for search
    full_prompt: str             # Full markdown content
    file_path: str               # Source file location
    loaded_at: datetime          # For cache invalidation
```

### Session State

```python
@dataclass
class AgentSession:
    session_id: str
    current_agent_id: Optional[str]
    topic_context: str           # Brief topic description
    message_count: int           # Messages with this agent
    agent_history: List[str]     # Previous agents in session
    created_at: datetime
    updated_at: datetime
```

### Classification Result

```python
@dataclass
class ClassificationResult:
    agent_id: str
    confidence: float            # 0.0 - 1.0
    reasoning: str               # Why this agent was selected
    is_explicit_request: bool    # User explicitly asked for agent
    is_multi_domain: bool        # Request spans multiple domains
    secondary_agents: List[str]  # For multi-domain requests
    topic_summary: str           # Brief topic description
```

### Agent Registry Index

```python
class AgentRegistry:
    agents: Dict[str, AgentDefinition]           # id → agent
    by_category: Dict[str, List[str]]            # category → [agent_ids]
    keyword_index: Dict[str, List[str]]          # keyword → [agent_ids]
    capability_embeddings: Optional[np.ndarray]  # Future: semantic search
```

---

## API Design

### Internal APIs (Within Conversation Service)

#### Agent Router Interface

```python
class AgentRouter:
    async def route(
        self,
        message: str,
        session_id: str,
        conversation_history: List[Message],
        force_agent: Optional[str] = None
    ) -> RoutingResult:
        """
        Main routing method.

        Returns:
            RoutingResult with selected agent(s) and composed prompt
        """

    async def get_agent_info(self, agent_id: str) -> AgentDefinition:
        """Get full agent definition by ID."""

    async def list_agents(
        self,
        category: Optional[str] = None
    ) -> List[AgentSummary]:
        """List available agents, optionally filtered by category."""

    async def search_agents(self, query: str) -> List[AgentMatch]:
        """Search agents by capability/keyword."""
```

#### Routing Result

```python
@dataclass
class RoutingResult:
    primary_agent: Optional[AgentDefinition]
    secondary_agents: List[AgentDefinition]      # For multi-domain
    composed_prompt: str                          # Ready-to-use prompt
    handoff_text: Optional[str]                   # Introduction text
    classification: ClassificationResult
    cache_hit: bool                               # Was agent from cache?
```

### Modified Conversation Endpoint

```python
# Existing endpoint with new optional parameters
@app.post("/conversation/message")
async def handle_message(
    request: ConversationRequest,
    force_agent: Optional[str] = Query(None),    # NEW: Explicit agent override
    include_agent_info: bool = Query(False)      # NEW: Include routing metadata
) -> ConversationResponse:
    ...

# Response model extended
class ConversationResponse(BaseModel):
    message: str
    # ... existing fields ...
    agent_info: Optional[AgentInfo] = None       # NEW

class AgentInfo(BaseModel):
    agent_id: Optional[str]
    agent_name: Optional[str]
    confidence: Optional[float]
    handoff_used: bool
```

### New Agent Information Endpoints

```python
@app.get("/agents")
async def list_agents(
    category: Optional[str] = None
) -> List[AgentSummary]:
    """List all available agents or filter by category."""

@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> AgentDefinition:
    """Get detailed information about a specific agent."""

@app.get("/agents/categories")
async def list_categories() -> List[CategoryInfo]:
    """List all agent categories with counts."""

@app.post("/agents/reload")
async def reload_agents() -> ReloadResult:
    """Hot-reload agent definitions from filesystem."""
```

---

## Non-Goals / Out of Scope

### Explicitly Not Included

1. **Parallel Agent Consultation** - Multi-domain requests will use sequential consultation only. Parallel execution adds complexity without proportional benefit for this use case.

2. **Agent-Specific LLM Models** - All agents will use the same underlying LLM (Bedrock Claude). Different model routing per agent is out of scope.

3. **Agent Learning/Fine-tuning** - Agents are static definitions. No learning from user interactions or dynamic capability updates.

4. **Agent Authentication/Permissions** - All agents are available to all users. No role-based agent access control.

5. **Agent Creation UI** - Agents are managed via markdown files. No web interface for creating/editing agents.

6. **Cross-Service Agent Routing** - Agents only affect the conversation service. Other microservices (weather, calendar, etc.) remain unchanged.

7. **Agent Performance Metrics** - No tracking of which agents perform best or user satisfaction per agent.

8. **Embedding-Based Semantic Search** - Initial implementation uses keyword matching. Semantic search via embeddings is a future enhancement.

9. **Agent Versioning** - No version control for agent definitions. File-based storage provides implicit history via git.

10. **Multi-Language Agent Prompts** - All agents defined in English. Internationalization is out of scope.

11. **Agent Marketplace/Sharing** - Agents are project-local. No mechanism for sharing agents between JARVIS installations.

12. **Voice-Specific Agent Personas** - Agents affect text responses only. No custom TTS voices per agent.

---

## Implementation Phases

### Phase 1: Foundation
- Copy agent definitions from claude_agents to JARVIS
- Implement AgentRegistry with file loading
- Create agent data models
- Add basic agent listing endpoints

### Phase 2: Classification
- Implement Intent Classifier with Haiku
- Add explicit agent request detection
- Create classification prompt templates
- Add confidence thresholds and fallback logic

### Phase 3: Routing Integration
- Implement Session Cache with Redis
- Create Prompt Composer
- Integrate router into main conversation flow
- Add handoff text generation

### Phase 4: Multi-Agent Support
- Implement multi-domain detection
- Add sequential agent consultation
- Create response synthesis logic
- Handle agent transitions gracefully

### Phase 5: Polish & Testing
- Add hot-reload capability
- Implement topic change detection
- Create comprehensive test suite
- Performance optimization

---

## Configuration

### Environment Variables

```bash
# Agent Routing
AGENT_ROUTING_ENABLED=true
AGENT_DEFINITIONS_PATH=/app/agents
AGENT_CLASSIFICATION_MODEL=anthropic.claude-3-haiku-20240307-v1:0
AGENT_CONFIDENCE_THRESHOLD=0.6
AGENT_MULTI_DOMAIN_THRESHOLD=0.5

# Session Cache
AGENT_SESSION_TTL_SECONDS=3600
AGENT_TOPIC_CHANGE_THRESHOLD=0.7

# Performance
AGENT_CLASSIFICATION_TIMEOUT_MS=500
AGENT_MAX_SECONDARY_AGENTS=3
```

---

*Generated: 2025-01-24*
*Project: JARVIS Agent Routing System*
