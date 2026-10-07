"""
Clause Graph Service
Builds a lightweight clause relationship graph using NetworkX.
Computes degree centrality to identify structurally important clauses.
Detects cross-references between sections for structure awareness.
"""

import re
import logging
from collections import defaultdict
from typing import Optional

import networkx as nx

logger = logging.getLogger(__name__)

# Legal keywords used to detect clause connections
LEGAL_KEYWORDS = [
    "indemnif", "liability", "damage", "terminat", "breach", "default",
    "warrant", "represent", "obligat", "covenant", "restrict", "prohibit",
    "assign", "transfer", "license", "confiden", "proprietary", "intellectual",
    "property", "patent", "copyright", "trademark", "exclusiv", "compet",
    "solicit", "govern", "jurisdict", "arbitrat", "remedy", "enforce",
    "waiver", "amend", "notice", "renewal", "expir", "insur", "audit",
    "payment", "fee", "royalt", "penalt", "force majeure", "negligence",
]

# Minimum shared keywords to create an edge
MIN_SHARED_KEYWORDS = 2

# Pattern to detect cross-references like "Section 3", "Article 5.1", "Clause 2(a)"
SECTION_REF_PATTERN = re.compile(
    r"(?:(?:section|article|clause|paragraph|part)\s+(\d+(?:\.\d+)*))"
    r"|(?:§\s*(\d+(?:\.\d+)*))",
    re.IGNORECASE,
)


class ClauseGraph:
    """Builds a graph of clause relationships and computes centrality."""

    def build_graph(self, clauses: list[dict]) -> dict:
        """
        Build a clause relationship graph and compute degree centrality.

        Args:
            clauses: List of clause dicts with 'id', 'text', 'section_heading'

        Returns:
            Dict with:
                - centrality: dict mapping clause_id → centrality score (0.0 to 1.0)
                - stats: dict with nodes, edges, max_centrality, components
        """
        if not clauses or len(clauses) < 2:
            centrality = {c["id"]: 0.0 for c in clauses} if clauses else {}
            return {
                "centrality": centrality,
                "stats": {"nodes": len(clauses), "edges": 0, "max_centrality": 0.0, "components": len(clauses)},
            }

        try:
            G = nx.Graph()

            # Step 1: Add all clauses as nodes
            for clause in clauses:
                G.add_node(clause["id"], section=clause.get("section_heading", ""))

            # Step 2: Extract keyword sets for each clause
            clause_keywords = {}
            for clause in clauses:
                keywords = self._extract_keywords(clause["text"])
                clause_keywords[clause["id"]] = keywords

            # Step 3: Create edges based on shared keywords
            clause_ids = list(clause_keywords.keys())
            for i in range(len(clause_ids)):
                for j in range(i + 1, len(clause_ids)):
                    id_a, id_b = clause_ids[i], clause_ids[j]
                    shared = clause_keywords[id_a] & clause_keywords[id_b]

                    if len(shared) >= MIN_SHARED_KEYWORDS:
                        # Weight = number of shared keywords
                        G.add_edge(id_a, id_b, weight=len(shared), shared_keywords=list(shared))

            # Step 4: Add edges for same-section clauses
            section_groups = defaultdict(list)
            for clause in clauses:
                section = clause.get("section_heading", "").strip().lower()
                if section and section not in ("general", "preamble", ""):
                    section_groups[section].append(clause["id"])

            for section, ids in section_groups.items():
                for i in range(len(ids)):
                    for j in range(i + 1, len(ids)):
                        if not G.has_edge(ids[i], ids[j]):
                            G.add_edge(ids[i], ids[j], weight=1, shared_keywords=["same_section"])

            # Step 5: Add edges based on cross-references
            self._add_reference_edges(G, clauses)

            # Step 6: Compute degree centrality
            if G.number_of_edges() > 0:
                centrality = nx.degree_centrality(G)
            else:
                centrality = {node: 0.0 for node in G.nodes()}

            max_cent = max(centrality.values()) if centrality else 0.0
            num_components = nx.number_connected_components(G) if G.number_of_nodes() > 0 else 0

            stats = {
                "nodes": G.number_of_nodes(),
                "edges": G.number_of_edges(),
                "max_centrality": round(max_cent, 4),
                "components": num_components,
            }

            logger.info(
                f"Clause graph: {stats['nodes']} nodes, {stats['edges']} edges, "
                f"max centrality: {stats['max_centrality']:.3f}, components: {stats['components']}"
            )

            return {"centrality": centrality, "stats": stats}

        except Exception as e:
            logger.error(f"Graph construction failed: {e}")
            # Fail-safe: return 0 centrality for all
            centrality = {c["id"]: 0.0 for c in clauses}
            return {
                "centrality": centrality,
                "stats": {"nodes": len(clauses), "edges": 0, "max_centrality": 0.0, "components": len(clauses)},
            }

    def _add_reference_edges(self, G: nx.Graph, clauses: list[dict]):
        """
        Detect cross-references (e.g. 'Section 5', 'Article 3.1') in clause text
        and create edges between referencing and referenced clauses.
        """
        # Build a map: section number string → clause IDs
        section_map = defaultdict(list)
        for clause in clauses:
            heading = clause.get("section_heading", "")
            # Extract numbers from section heading
            nums = re.findall(r"(\d+(?:\.\d+)*)", heading)
            for num in nums:
                section_map[num].append(clause["id"])

        # For each clause, find references to other sections
        for clause in clauses:
            refs = self._extract_section_references(clause["text"])
            for ref_num in refs:
                target_ids = section_map.get(ref_num, [])
                for target_id in target_ids:
                    if target_id != clause["id"] and not G.has_edge(clause["id"], target_id):
                        G.add_edge(
                            clause["id"], target_id,
                            weight=2,
                            shared_keywords=["cross_reference"],
                        )

    def _extract_section_references(self, text: str) -> set[str]:
        """Extract section/article/clause number references from text."""
        refs = set()
        for match in SECTION_REF_PATTERN.finditer(text):
            # Group 1: "Section X" style, Group 2: "§X" style
            ref = match.group(1) or match.group(2)
            if ref:
                refs.add(ref)
        return refs

    def _extract_keywords(self, text: str) -> set[str]:
        """Extract legal keywords present in the clause text."""
        text_lower = text.lower()
        found = set()
        for keyword in LEGAL_KEYWORDS:
            if keyword in text_lower:
                found.add(keyword)
        return found


clause_graph = ClauseGraph()
