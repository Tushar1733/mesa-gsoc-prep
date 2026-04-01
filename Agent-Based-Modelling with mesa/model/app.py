"""
app.py — Frontier Worlds Interactive Dashboard
================================================
Run with:
    solara run app.py

Controls:
  • Sliders to configure n_colonies, edge_prob, seed
  • Step / Run / Reset buttons
  • Live network plot   — ideology (fill), faction (border), wealth (size)
  • Live time-series    — # factions, mean ideology, wealth Gini
"""

import random
import colorsys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import networkx as nx
import solara

from fw_model import FrontierWorldsModel
from fw_agent import ColonyAgent

# ---------------------------------------------------------------------------
# Reactive state
# ---------------------------------------------------------------------------
model_state   = solara.reactive(None)   # holds the FrontierWorldsModel instance
running       = solara.reactive(False)  # auto-run toggle
step_count    = solara.reactive(0)

# Sliders (used before model creation / on reset)
n_colonies_sl = solara.reactive(20)
edge_prob_sl  = solara.reactive(0.25)
seed_sl       = solara.reactive(42)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_model():
    m = FrontierWorldsModel(
        n_colonies=n_colonies_sl.value,
        edge_prob=edge_prob_sl.value,
        seed=seed_sl.value,
    )
    model_state.value = m
    step_count.value  = 0


def _faction_palette(n):
    """Return n visually distinct RGBA colours."""
    return [colorsys.hsv_to_rgb(i / max(n, 1), 0.8, 0.9) + (1.0,)
            for i in range(n)]


# ---------------------------------------------------------------------------
# Network figure
# ---------------------------------------------------------------------------

def draw_network(model: FrontierWorldsModel):
    G   = model.G
    pos = nx.spring_layout(G, seed=model_state.value.step_count % 100 + 1)

    agents      = model.agent_map
    factions    = sorted({a.faction for a in agents.values()})
    palette     = _faction_palette(len(factions))
    f_color     = {f: palette[i] for i, f in enumerate(factions)}

    node_colors  = [agents[n].ideology for n in G.nodes()]
    edge_colors  = [f_color.get(agents[n].faction, (0.5,0.5,0.5,1)) for n in G.nodes()]
    node_sizes   = [max(60, agents[n].wealth * 5) for n in G.nodes()]
    labels       = {n: str(n) for n in G.nodes()}

    fig, ax = plt.subplots(figsize=(6, 5))
    fig.patch.set_facecolor("#0d0d1a")
    ax.set_facecolor("#0d0d1a")
    ax.axis("off")
    ax.set_title(f"Step {model.step_count}  |  Factions: "
                 f"{len(factions)}", color="white", fontsize=11)

    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.25,
                           edge_color="white", width=0.6)
    nx.draw_networkx_nodes(G, pos, ax=ax,
                           node_color=node_colors,
                           node_size=node_sizes,
                           cmap="coolwarm", vmin=0, vmax=1,
                           linewidths=2,
                           edgecolors=edge_colors)
    nx.draw_networkx_labels(G, pos, labels=labels, ax=ax,
                            font_size=7, font_color="white")

    sm = plt.cm.ScalarMappable(cmap="coolwarm",
                                norm=mcolors.Normalize(0, 1))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Ideology", color="white", fontsize=8)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Time-series figure
# ---------------------------------------------------------------------------

def draw_timeseries(model: FrontierWorldsModel):
    df = model.datacollector.get_model_vars_dataframe()

    fig, axes = plt.subplots(1, 3, figsize=(11, 3))
    fig.patch.set_facecolor("#0d0d1a")

    metrics = ["Num_Factions", "Mean_Ideology", "Wealth_Gini"]
    titles  = ["# Factions",   "Mean Ideology",  "Wealth Gini"]
    colors  = ["#7ec8e3",      "#f4a261",         "#e63946"]

    for ax, metric, title, color in zip(axes, metrics, titles, colors):
        ax.set_facecolor("#0d0d1a")
        ax.tick_params(colors="white", labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor("#333")
        ax.set_title(title, color="white", fontsize=9)
        ax.set_xlabel("Step", color="white", fontsize=8)
        if not df.empty:
            ax.plot(df.index, df[metric], color=color, lw=1.8)
            ax.fill_between(df.index, df[metric], alpha=0.15, color=color)
        ax.grid(alpha=0.12, color="white")

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Solara components
# ---------------------------------------------------------------------------

@solara.component
def ControlPanel():
    solara.Text("⚙️ Configuration", style="color:#7ec8e3;font-weight:bold;font-size:15px")
    solara.SliderInt("Colonies",   value=n_colonies_sl, min=10, max=60, step=5)
    solara.SliderFloat("Edge prob",value=edge_prob_sl,  min=0.1, max=0.6, step=0.05)
    solara.SliderInt("Seed",       value=seed_sl,       min=0, max=200, step=1)

    with solara.Row():
        solara.Button("🔄 Reset",  on_click=lambda: (_make_model(), running.set(False)),
                      color="primary")
        solara.Button("▶ Step",
                      on_click=lambda: (model_state.value.step(),
                                        step_count.set(step_count.value + 1))
                      if model_state.value else None,
                      color="secondary")

    solara.Switch(label="⚡ Auto-run", value=running)

    if model_state.value:
        m = model_state.value
        df = m.datacollector.get_model_vars_dataframe()
        solara.Text(f"Step: {m.step_count}", style="color:white")
        if not df.empty:
            last = df.iloc[-1]
            solara.Text(f"Factions: {int(last['Num_Factions'])}",
                        style="color:#57cc99")
            solara.Text(f"Mean ideology: {last['Mean_Ideology']:.3f}",
                        style="color:#f4a261")
            solara.Text(f"Wealth Gini: {last['Wealth_Gini']:.3f}",
                        style="color:#e63946")


@solara.component
def NetworkPanel():
    if model_state.value is None:
        solara.Text("Press Reset to initialise the model.",
                    style="color:#aaa")
        return
    fig = draw_network(model_state.value)
    solara.FigureMatplotlib(fig)
    plt.close(fig)


@solara.component
def TimeSeriesPanel():
    if model_state.value is None:
        return
    fig = draw_timeseries(model_state.value)
    solara.FigureMatplotlib(fig)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Auto-run timer
# ---------------------------------------------------------------------------

def use_interval(callback, enabled: bool, ms: int = 300):
    """Simple polling interval via solara.use_effect."""
    counter = solara.use_reactive(0)

    def tick():
        if enabled:
            callback()
            counter.set(counter.value + 1)

    solara.use_thread(tick, dependencies=[counter.value, enabled])


# ---------------------------------------------------------------------------
# Root Page
# ---------------------------------------------------------------------------

@solara.component
def Page():
    # Initialise model on first render
    if model_state.value is None:
        _make_model()

    # Auto-step
    def auto_step():
        import time
        while running.value and model_state.value is not None:
            model_state.value.step()
            step_count.set(step_count.value + 1)
            time.sleep(0.3)

    solara.use_thread(auto_step, dependencies=[running.value])

    # Layout
    solara.Title("🚀 Frontier Worlds — Space Colonisation ABM")

    with solara.Columns([1, 3]):
        # Left: controls + stats
        with solara.Column():
            ControlPanel()

        # Right: visuals
        with solara.Column():
            NetworkPanel()
            TimeSeriesPanel()