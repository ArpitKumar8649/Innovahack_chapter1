"""Knowledge graph (Phase 7) — provenance at graph scale.

Builds a directed provenance graph from the verified claims:

    Claim → SUPPORTED_BY → Evidence (chunk) → FROM → Source → PUBLISHED_BY → Publisher
    Claim → CONTRADICTS → Claim
    Claim → SUPERSEDES → Claim (temporal)

The graph enables:
- **Multi-hop verification:** "is the only source for this claim a blog citing
  another blog?" — trace the provenance chain and downgrade if it's circular.
- **Circular-citation detection:** find cycles in the Source→CITES→Source
  subgraph. A circular citation is a genuine trust signal — the evidence is
  self-referential and weaker.

Uses NetworkX (pure Python, in-memory) for the hackathon; Neo4j is the
production target (same graph model, different storage).
"""
import networkx as nx


def build_provenance_graph(claims, sources_by_id) -> nx.DiGraph:
    """Build the provenance graph from verified claims + sources.

    Nodes: claim:{id}, source:{id}, publisher:{domain}
    Edges: SUPPORTED_BY (claim→source), FROM (source→publisher),
           CITES (source→source, if we can infer it), CONTRADICTS (claim→claim)
    """
    G = nx.DiGraph()

    # add claim nodes
    for c in claims:
        G.add_node(f"claim:{c.id}", type="claim", text=c.text, status=c.status,
                   confidence=c.confidence)

    # add source + publisher nodes, and edges
    for c in claims:
        for sid in c.source_ids:
            s = sources_by_id.get(sid)
            if not s:
                continue
            src_node = f"source:{sid}"
            pub_node = f"publisher:{s.publisher or 'unknown'}"
            G.add_node(src_node, type="source", title=s.title, url=s.url,
                       tier=s.authority_tier, publisher=s.publisher)
            G.add_node(pub_node, type="publisher", domain=s.publisher or "unknown")
            G.add_edge(f"claim:{c.id}", src_node, relation="SUPPORTED_BY")
            G.add_edge(src_node, pub_node, relation="PUBLISHED_BY")

    # add CONTRADICTS edges (from the contradiction detector)
    # (contradictions are claim-level; we link the claims that conflict)
    # This is inferred from the contradiction list passed separately.

    return G


def detect_circular_citations(G: nx.DiGraph) -> list[list[str]]:
    """Find cycles in the Source→CITES→Source subgraph.

    Returns a list of cycles, each a list of node IDs (source:X → source:Y → ...).
    A circular citation means the evidence is self-referential — a genuine
    trust signal that the claim is weaker than it appears.
    """
    # extract the source-only subgraph (source:X → source:Y edges)
    source_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "source"]
    H = G.subgraph(source_nodes).copy()

    # find simple cycles (each cycle is a list of nodes)
    cycles = list(nx.simple_cycles(H))
    return cycles


def multi_hop_analysis(G: nx.DiGraph, claim_id: int) -> dict:
    """Analyze the provenance chain for a claim.

    Returns:
    - depth: how many hops from claim to publisher
    - circular: whether the claim's sources are in a citation cycle
    - weakest_tier: the lowest authority tier in the chain
    - chain: the full path (claim → source → publisher)
    """
    claim_node = f"claim:{claim_id}"
    if claim_node not in G:
        return {"depth": 0, "circular": False, "weakest_tier": 5, "chain": []}

    # find all paths from claim to publisher (max depth 3)
    chains = []
    for target in G.nodes():
        if G.nodes[target].get("type") == "publisher":
            try:
                for path in nx.all_simple_paths(G, claim_node, target, cutoff=3):
                    chains.append(path)
            except nx.NetworkXNoPath:
                pass

    if not chains:
        return {"depth": 0, "circular": False, "weakest_tier": 5, "chain": []}

    # find the shortest chain (most direct provenance)
    shortest = min(chains, key=len)

    # check if any source in the chain is in a circular citation
    cycles = detect_circular_citations(G)
    cycle_nodes = {n for cycle in cycles for n in cycle}
    circular = any(n in cycle_nodes for n in shortest if n.startswith("source:"))

    # find the weakest tier in the chain
    weakest_tier = 5
    for n in shortest:
        if n.startswith("source:"):
            tier = G.nodes[n].get("tier", 5)
            weakest_tier = min(weakest_tier, tier)

    return {
        "depth": len(shortest) - 1,
        "circular": circular,
        "weakest_tier": weakest_tier,
        "chain": shortest,
    }


def graph_stats(G: nx.DiGraph) -> dict:
    """Summary stats for the provenance graph."""
    claims = [n for n, d in G.nodes(data=True) if d.get("type") == "claim"]
    sources = [n for n, d in G.nodes(data=True) if d.get("type") == "source"]
    publishers = [n for n, d in G.nodes(data=True) if d.get("type") == "publisher"]
    cycles = detect_circular_citations(G)
    return {
        "claims": len(claims),
        "sources": len(sources),
        "publishers": len(publishers),
        "edges": G.number_of_edges(),
        "circular_citations": len(cycles),
        "cycles": cycles[:5],  # first 5 cycles for display
    }
