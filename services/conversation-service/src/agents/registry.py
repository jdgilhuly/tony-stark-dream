"""Agent registry for loading and indexing agent definitions."""

import logging
import os
import re
from pathlib import Path
from datetime import datetime
from functools import lru_cache

import yaml

from .models import AgentDefinition, AgentSummary, CategoryInfo

logger = logging.getLogger(__name__)

# Category name mappings
CATEGORY_NAMES = {
    "01-core-development": "Core Development",
    "02-language-specialists": "Language Specialists",
    "03-infrastructure": "Infrastructure",
    "04-quality-security": "Quality & Security",
    "05-data-ai": "Data & AI",
    "06-developer-experience": "Developer Experience",
    "07-specialized-domains": "Specialized Domains",
    "08-business-product": "Business & Product",
    "09-meta-orchestration": "Meta & Orchestration",
    "10-research-analysis": "Research & Analysis",
}

# Common keywords to extract from agent content
KEYWORD_PATTERNS = [
    r"python|javascript|typescript|java|golang|rust|c\+\+|swift|kotlin",
    r"react|vue|angular|nextjs|django|flask|fastapi|rails|spring",
    r"aws|azure|gcp|kubernetes|docker|terraform|ansible",
    r"postgresql|mysql|mongodb|redis|elasticsearch",
    r"security|testing|performance|debugging|deployment",
    r"api|graphql|rest|websocket|grpc",
    r"machine learning|ml|ai|data science|nlp",
    r"devops|sre|infrastructure|cloud|networking",
]


class AgentRegistry:
    """Registry for loading and managing agent definitions."""

    def __init__(self, agents_path: str):
        self.agents_path = Path(agents_path)
        self.agents: dict[str, AgentDefinition] = {}
        self.by_category: dict[str, list[str]] = {}
        self.keyword_index: dict[str, list[str]] = {}
        self._loaded = False

    def load_agents(self) -> int:
        """Load all agent definitions from the filesystem."""
        if not self.agents_path.exists():
            logger.warning(f"Agents path does not exist: {self.agents_path}")
            return 0

        self.agents.clear()
        self.by_category.clear()
        self.keyword_index.clear()

        loaded_count = 0

        # Iterate through category directories
        for category_dir in sorted(self.agents_path.iterdir()):
            if not category_dir.is_dir() or category_dir.name.startswith("."):
                continue

            category_id = category_dir.name
            category_name = CATEGORY_NAMES.get(category_id, category_id)

            if category_id not in self.by_category:
                self.by_category[category_id] = []

            # Load agent files in this category
            for agent_file in sorted(category_dir.glob("*.md")):
                if agent_file.name == "README.md":
                    continue

                try:
                    agent = self._parse_agent_file(agent_file, category_id, category_name)
                    if agent:
                        self.agents[agent.id] = agent
                        self.by_category[category_id].append(agent.id)
                        self._index_agent_keywords(agent)
                        loaded_count += 1
                except Exception as e:
                    logger.error(f"Failed to parse agent file {agent_file}: {e}")

        self._loaded = True
        logger.info(f"Loaded {loaded_count} agents from {len(self.by_category)} categories")
        return loaded_count

    def _parse_agent_file(
        self, file_path: Path, category_id: str, category_name: str
    ) -> AgentDefinition | None:
        """Parse a single agent markdown file."""
        content = file_path.read_text(encoding="utf-8")

        # Parse YAML frontmatter
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not frontmatter_match:
            logger.warning(f"No frontmatter found in {file_path}")
            return None

        frontmatter_text = frontmatter_match.group(1)
        body_text = frontmatter_match.group(2).strip()

        try:
            frontmatter = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML frontmatter in {file_path}: {e}")
            return None

        # Extract required fields
        agent_id = frontmatter.get("name", file_path.stem)
        description = frontmatter.get("description", "")
        tools_str = frontmatter.get("tools", "")

        # Parse tools list
        tools = [t.strip() for t in tools_str.split(",")] if tools_str else []

        # Extract expertise areas from content
        expertise_areas = self._extract_expertise_areas(body_text)

        # Generate keywords
        keywords = self._extract_keywords(agent_id, description, body_text)

        # Create human-readable name from ID
        name = agent_id.replace("-", " ").title()

        return AgentDefinition(
            id=agent_id,
            name=name,
            description=description,
            category=category_id,
            category_name=category_name,
            tools=tools,
            expertise_areas=expertise_areas,
            keywords=keywords,
            full_prompt=body_text,
            file_path=str(file_path),
            loaded_at=datetime.utcnow(),
        )

    def _extract_expertise_areas(self, content: str) -> list[str]:
        """Extract expertise areas from agent content."""
        areas = []

        # Look for checklist items and section headers
        lines = content.split("\n")
        for line in lines:
            # Match markdown list items with expertise-like content
            if line.strip().startswith("- ") and len(line) < 100:
                item = line.strip()[2:].strip()
                # Filter out generic items
                if len(item) > 5 and not item.startswith("```"):
                    areas.append(item)
            # Match section headers
            elif line.startswith("## ") or line.startswith("### "):
                header = line.lstrip("#").strip()
                if header and "protocol" not in header.lower() and "workflow" not in header.lower():
                    areas.append(header)

        # Deduplicate and limit
        seen = set()
        unique_areas = []
        for area in areas[:50]:  # Limit to 50 areas
            normalized = area.lower()
            if normalized not in seen:
                seen.add(normalized)
                unique_areas.append(area)

        return unique_areas[:30]  # Return top 30

    def _extract_keywords(self, agent_id: str, description: str, content: str) -> list[str]:
        """Extract searchable keywords from agent content."""
        keywords = set()

        # Add words from agent ID
        keywords.update(agent_id.split("-"))

        # Add words from description
        desc_words = re.findall(r"\b[a-z]{3,}\b", description.lower())
        keywords.update(desc_words)

        # Find technical terms in content
        combined_pattern = "|".join(KEYWORD_PATTERNS)
        found_keywords = re.findall(combined_pattern, content.lower())
        keywords.update(found_keywords)

        # Filter common words
        stop_words = {
            "the", "and", "for", "with", "that", "this", "from", "are", "was",
            "will", "can", "has", "have", "your", "you", "use", "using", "when",
            "all", "any", "each", "into", "through", "during", "before", "after",
        }
        keywords = {k for k in keywords if k not in stop_words and len(k) > 2}

        return sorted(list(keywords))[:50]  # Limit to 50 keywords

    def _index_agent_keywords(self, agent: AgentDefinition) -> None:
        """Add agent to keyword index."""
        for keyword in agent.keywords:
            if keyword not in self.keyword_index:
                self.keyword_index[keyword] = []
            self.keyword_index[keyword].append(agent.id)

    def get_agent(self, agent_id: str) -> AgentDefinition | None:
        """Get an agent by ID."""
        if not self._loaded:
            self.load_agents()
        return self.agents.get(agent_id)

    def get_all_agents(self) -> list[AgentDefinition]:
        """Get all loaded agents."""
        if not self._loaded:
            self.load_agents()
        return list(self.agents.values())

    def get_agents_by_category(self, category: str) -> list[AgentDefinition]:
        """Get all agents in a category."""
        if not self._loaded:
            self.load_agents()
        agent_ids = self.by_category.get(category, [])
        return [self.agents[aid] for aid in agent_ids if aid in self.agents]

    def search_by_keyword(self, keyword: str) -> list[AgentDefinition]:
        """Search agents by keyword."""
        if not self._loaded:
            self.load_agents()

        keyword = keyword.lower()
        matching_ids = set()

        # Exact keyword match
        if keyword in self.keyword_index:
            matching_ids.update(self.keyword_index[keyword])

        # Partial match in keywords
        for kw, agent_ids in self.keyword_index.items():
            if keyword in kw or kw in keyword:
                matching_ids.update(agent_ids)

        return [self.agents[aid] for aid in matching_ids if aid in self.agents]

    def get_categories(self) -> list[CategoryInfo]:
        """Get all categories with their agents."""
        if not self._loaded:
            self.load_agents()

        categories = []
        for category_id, agent_ids in sorted(self.by_category.items()):
            category_name = CATEGORY_NAMES.get(category_id, category_id)
            categories.append(
                CategoryInfo(
                    id=category_id,
                    name=category_name,
                    description=f"Agents specializing in {category_name.lower()}",
                    agent_count=len(agent_ids),
                    agent_ids=agent_ids,
                )
            )
        return categories

    def get_agent_summaries(self) -> list[AgentSummary]:
        """Get summaries of all agents for classification prompt."""
        if not self._loaded:
            self.load_agents()

        return [agent.to_summary() for agent in self.agents.values()]

    def reload(self) -> tuple[int, list[str]]:
        """Reload all agents, return (count, errors)."""
        errors = []
        self._loaded = False

        try:
            count = self.load_agents()
            return count, errors
        except Exception as e:
            errors.append(str(e))
            return 0, errors


# Singleton instance
_registry: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    """Get the agent registry singleton."""
    global _registry
    if _registry is None:
        # Default path relative to this file
        agents_path = os.environ.get(
            "AGENT_DEFINITIONS_PATH",
            str(Path(__file__).parent.parent.parent / "agents")
        )
        _registry = AgentRegistry(agents_path)
        _registry.load_agents()
    return _registry
