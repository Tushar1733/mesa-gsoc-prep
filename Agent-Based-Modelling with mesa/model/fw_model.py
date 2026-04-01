"""
model.py — Frontier Worlds
===========================
Defines FrontierWorldsModel and the faction-assignment helper.
"""

import random
import networkx as nx
from mesa import Model
from mesa.datacollection import DataCollector

from fw_agent import ColonyAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def gini(values):
    """Gini coefficient for a list of non-negative values."""
    v = sorted(values)
    n = len(v)
    if n == 0 or sum(v) == 0:
        return 0.0
    cumsum = sum((2 * (i + 1) - n - 1) * x for i, x in enumerate(v))
    return cumsum / (n * sum(v))


def assign_factions(model):
    """
    BFS over the network to cluster ideologically-similar neighbours
    into faction groups.  Colonies within THRESHOLD ideology of each
    other AND connected by an edge share a faction.
    """
    THRESHOLD = 0.25
    colony_agents = [a for a in model.agents if isinstance(a, ColonyAgent)]
    visited    = {}   # node_id -> faction_id
    faction_id = 0

    for agent in colony_agents:
        if agent.node_id in visited:
            continue
        queue = [agent]
        visited[agent.node_id] = faction_id
        while queue:
            current = queue.pop()
            for nb_id in model.G.neighbors(current.node_id):
                nb = model.agent_map[nb_id]
                if nb.node_id not in visited:
                    if abs(nb.ideology - current.ideology) < THRESHOLD:
                        visited[nb.node_id] = faction_id
                        queue.append(nb)
        faction_id += 1

    for agent in colony_agents:
        agent.faction = visited.get(agent.node_id, -1)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class FrontierWorldsModel(Model):
    """
    Space-colonisation ABM on a random network.

    Parameters
    ----------
    n_colonies : int   — number of star-system nodes (default 20)
    edge_prob  : float — Erdős–Rényi connection probability (default 0.25)
    seed       : int   — RNG seed for reproducibility (default 42)
    """

    def __init__(self, n_colonies: int = 20, edge_prob: float = 0.25, seed: int = 42):
        super().__init__(seed=seed)
        random.seed(seed)

        self.n_colonies = n_colonies
        self.step_count = 0

        # --- Build a connected random graph ---------------------------------
        self.G = nx.erdos_renyi_graph(n=n_colonies, p=edge_prob,
                                      seed=seed, directed=False)
        attempts = 0
        while not nx.is_connected(self.G) and attempts < 10:
            self.G = nx.erdos_renyi_graph(n=n_colonies,
                                          p=min(edge_prob + 0.05 * (attempts + 1), 0.9),
                                          seed=seed + attempts + 1, directed=False)
            attempts += 1

        # --- Create one ColonyAgent per node --------------------------------
        self.agent_map: dict[int, ColonyAgent] = {}
        for node in self.G.nodes():
            agent         = ColonyAgent(self)
            agent.node_id = node
            self.agent_map[node] = agent

        # --- Initial faction assignment -------------------------------------
        assign_factions(self)

        # --- Data collection ------------------------------------------------
        self.datacollector = DataCollector(
            model_reporters={
                "Num_Factions":    lambda m: len({a.faction for a in m.agents
                                                  if isinstance(a, ColonyAgent)}),
                "Mean_Ideology":   lambda m: (
                    sum(a.ideology for a in m.agents if isinstance(a, ColonyAgent))
                    / m.n_colonies),
                "Ideology_StdDev": lambda m: (
                    sum((a.ideology -
                         sum(x.ideology for x in m.agents if isinstance(x, ColonyAgent))
                         / m.n_colonies) ** 2
                        for a in m.agents if isinstance(a, ColonyAgent))
                    / m.n_colonies) ** 0.5,
                "Wealth_Gini":  lambda m: gini(
                    [a.wealth for a in m.agents if isinstance(a, ColonyAgent)]),
                "Total_Wealth": lambda m: sum(
                    a.wealth for a in m.agents if isinstance(a, ColonyAgent)),
            },
            agent_reporters={
                "Ideology":   "ideology",
                "Wealth":     "wealth",
                "Population": "population",
                "Faction":    "faction",
            },
        )
        self.datacollector.collect(self)

    # ------------------------------------------------------------------

    def step(self):
        self.step_count += 1
        for agent in list(self.agent_map.values()):
            agent.step()
        assign_factions(self)
        self.datacollector.collect(self)
