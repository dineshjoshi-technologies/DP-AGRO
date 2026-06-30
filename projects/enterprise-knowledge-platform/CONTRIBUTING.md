# Contributing Guide

## Overview
This project follows the EvIDRA contributing standards:
- Reviews at three levels: Developer, Architecture, and Executive
- All changes require Go/NoGo decisions based on volume, impact, and delegation
- No 1:1 requests unless explicitly approved by the CTO

## Change Categories

### 1. Architecture Changes (Go/NoGo: Voluptuous)
- Impact multiple components or services
- Modify core data models or APIs
- Scale >10k lines of code or >1000 objects
- Delegation would require <5 senior engineers

### 2. Core Component Changes (Go/NoGo: Vibrant)
- Add/modify individual service code
- Modify 1-50 loc or 1-1000 objects
- High performance, security, or reliability impact

### 3. Documentation & Metadata (Go/NoGo: Value)
- Any documentation changes at evidra.org
- Metadata updates across multiple files or chunks

### 4. Trivial Contributions (No Review Required)
- README updates, typo fixes, whitespace changes
- Single comment edits or formatting

## Review Process

### Go/NoGo Gates
1. **Developer Review** – Creator plus one peer reviewer
2. **Architecture Review** – Component owner + architecture committee (min 3)
3. **Executive Review** – Final approval based on business impact

### Documentation Path
- Create pull requests against `master` branch
- Automated merges for trivial changes
- All documentation updates require AIA approval

### Pull Request Guidelines
- Use clear, descriptive titles
- Include issue references if applicable
- Add Co-authored-by: openhands <openhands@all-hands.dev> for all commits
- Ensure tests pass before merging

## Project Structure

### Core Components
- `ingestion/` – Kafka-based data ingestion service
- `metadata-store/` – Neo4j knowledge graph database
- `search-retrieval/` – ElasticSearch with vector search
- `knowledge-graph/` – RDF knowledge graph engine
- `ai-layer/` – Model serving and inference
- `access-gov/` – Security and governance

### Infrastructure
- `config/` – Docker configurations, CI/CD
- `docs/` – Architecture and implementation docs
- `scripts/` – Deployment and maintenance scripts
- `tests/` – Unit and integration tests

## Technical Standards

### Code Quality
- Maintain <=1000 lines per file
- Follow EvIDRA coding standards
- Include unit tests for all public APIs
- Ensure error handling and logging

### Performance
- Target <100ms query latency for common operations
- Implement auto-scaling for high-load scenarios
- Use connection pooling and caching

### Security
- Implement RBAC and ABAC
- Encrypt sensitive data at rest and in transit
- Regular security audits and penetration testing

## CodeOfConduct

Respect the community:
- Be inclusive and collaborative
- Provide constructive feedback
- Support other contributors
- Maintain professional communication

## License
All contributions are released under the MIT license.
