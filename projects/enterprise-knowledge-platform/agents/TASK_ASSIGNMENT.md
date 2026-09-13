# Plant Research Task Assignment

## Paperclip Agent References
- CEO: [61ae0a1d](/DPA/agents/ceo)
- Botanical Research Agent: [e9e50eee](/DPA/agents/botanical-research-agent)
- Therapeutic & Market Research Agent: [67ee323d](/DPA/agents/therapeutic-market-research-agent)
- Data Structuring & AI Training Agent: [3a723709](/DPA/agents/data-structuring-ai-training-agent)

## Assigned Agents
1. **Botanical Research Agent** → `agents/botanical-research-agent.md` → [DPA-8](/DPA/issues/DPA-8)
2. **Therapeutic & Market Research Agent** → `agents/therapeutic-market-research-agent.md` → [DPA-9](/DPA/issues/DPA-9)
3. **Data Structuring & AI Training Agent** → `agents/data-structuring-agent.md` → [DPA-10](/DPA/issues/DPA-10)

## Execution Order
```
Phase 1: Agent 1 + Agent 2 (parallel research) → Phase 2: Agent 3 (data structuring)
```

## Phase 1 Tasks

### Agent 1: Botanical Research
- Priority: HIGH
- Deadline: Complete 1 plant per day minimum
- Start with: Neem (highest commercial priority)
- Deliverables: `/plant-research/raw-data/{plant}-botanical.yaml`
- Verification: Submit to CEO for review after first plant

### Agent 2: Therapeutic & Market Research
- Priority: HIGH
- Start with: Neem (highest commercial priority)
- Deliverables: `/plant-research/market-data/{plant}-therapeutic-market.yaml`
- Verification: Cross-reference with Agent 1 for compound consistency

## Phase 2 Tasks

### Agent 3: Data Structuring
- Start after: At least 3 plants completed in Phase 1
- Priority: HIGH
- Deliverables:
  - Schema: `schema/plant-knowledge-schema.json`
  - Knowledge Graph: `ai-ready/knowledge-graph/`
  - RAG Docs: `ai-ready/rag-docs/`
  - Fine-Tuning Data: `ai-ready/fine-tuning/`
  - Quality Report: `data-quality-report.md`
- Verification: 100% schema validation

## Skills Required
- Agents 1 & 2: Web research, scientific literature review, data extraction, YAML authoring
- Agent 3: JSON Schema design, knowledge graph modeling, NLP data preparation, data validation

## Governance
- All agents must follow the company's knowledge management standards
- Daily progress reports expected
- Escalate data conflicts to the Chief Research Officer
- Final deliverables undergo CEO approval before AI training use

## Quality Gates
1. Research complete and cited → Gate 1
2. Data validated against schema → Gate 2
3. AI datasets generated and verified → Gate 3
4. CEO/CTO final review → Gate 4 (DONE)
