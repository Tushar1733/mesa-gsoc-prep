"""
agent.py — Frontier Worlds
===========================
Defines the ColonyAgent that lives on a star-system node.
"""

import random
from mesa import Agent


class ColonyAgent(Agent):
    """
    A colony on a star-system node.

    Attributes
    ----------
    node_id    : int   — the NetworkX graph node this agent sits on
    ideology   : float — value in [0, 1]; drifts via neighbour influence
    wealth     : float — economic strength; grows via trade, shocked by events
    population : int   — colony size; can be reduced by disaster events
    faction    : int   — emergent group label assigned by the model each step
    """

    def __init__(self, model, ideology=None, wealth=None, population=None):
        super().__init__(model)
        self.node_id    = None                          # set by model after creation
        self.ideology   = ideology   if ideology   is not None else random.random()
        self.wealth     = wealth     if wealth     is not None else random.uniform(10, 100)
        self.population = population if population is not None else random.randint(100, 10_000)
        self.faction    = -1                            # assigned each step

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _influence_neighbours(self):
        """Spread ideology to connected colonies; wealthier colonies pull harder."""
        INFLUENCE_RATE = 0.05
        for nb_id in self.model.G.neighbors(self.node_id):
            nb   = self.model.agent_map[nb_id]
            diff = self.ideology - nb.ideology
            pull = INFLUENCE_RATE * (self.wealth / (self.wealth + nb.wealth))
            nb.ideology = max(0.0, min(1.0, nb.ideology + diff * pull))

    def _update_wealth(self):
        """Apply a random shock and a small trade bonus from neighbours."""
        shock        = random.uniform(-0.05, 0.05)
        neighbours   = [self.model.agent_map[n]
                        for n in self.model.G.neighbors(self.node_id)]
        trade_bonus  = (sum(n.wealth for n in neighbours) /
                        max(len(neighbours), 1)) * 0.01 if neighbours else 0
        self.wealth  = max(1.0, self.wealth * (1 + shock) + trade_bonus)

    def _random_event(self):
        """2 % chance of a resource boom or disaster each step."""
        roll = random.random()
        if roll < 0.02:
            self.wealth *= random.uniform(1.3, 2.0)          # boom
        elif roll < 0.04:
            self.wealth     *= random.uniform(0.3, 0.7)      # disaster
            self.population  = max(10, int(self.population * random.uniform(0.5, 0.9)))

    # ------------------------------------------------------------------
    # Mesa step
    # ------------------------------------------------------------------

    def step(self):
        self._influence_neighbours()
        self._update_wealth()
        self._random_event()
