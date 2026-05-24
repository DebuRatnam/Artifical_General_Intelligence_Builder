"""
world_map.py
Render a 2D top-down iconographic map of the agent's current Scene.

Uses Plotly with emoji text markers — each object becomes a labeled emoji
on a clean canvas, mirroring the reference layout (trash can, fan, table,
flower, water bottle, etc.) with audio sources annotated by frequency.
"""

from __future__ import annotations

import plotly.graph_objects as go

from world_model import Scene


# Reserve top strip of the canvas for audio source annotations.
_AUDIO_BAR_Y = 1.05
_AUDIO_X_SPACING = 0.35


# Build a Plotly Figure from the current Scene. Three layers:
# (1) emoji markers at each object's (x, y),
# (2) bold object labels below each emoji,
# (3) a faint confidence-tinted disc behind each icon.
# Audio sources are rendered as annotations in a strip above the canvas,
# each labeled with its bound FFT peak in Hz.
def render_scene(scene: Scene) -> go.Figure:
    fig = go.Figure()

    # ── Objects layer ────────────────────────────────────────────────────────
    if scene.objects:
        xs = [o.x for o in scene.objects.values()]
        ys = [o.y for o in scene.objects.values()]
        icons = [o.icon for o in scene.objects.values()]
        labels = [o.label for o in scene.objects.values()]
        opacities = [max(0.35, o.confidence) for o in scene.objects.values()]

        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="text",
            text=icons,
            textfont=dict(size=44),
            textposition="middle center",
            hovertext=labels,
            hoverinfo="text",
            opacity=1.0,
            showlegend=False,
        ))

        # Label below each icon
        fig.add_trace(go.Scatter(
            x=xs,
            y=[y - 0.06 for y in ys],
            mode="text",
            text=[f"<b>{l}</b>" for l in labels],
            textfont=dict(size=14, color="#222"),
            textposition="bottom center",
            showlegend=False,
            hoverinfo="skip",
        ))
        # Confidence wash (faint colored disc behind icon)
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="markers",
            marker=dict(size=80, color="rgba(120,180,240,0.25)", line=dict(width=0)),
            opacity=1.0,
            showlegend=False,
            hoverinfo="skip",
        ))
    else:
        fig.add_annotation(
            x=0.5, y=0.5, xref="x", yref="y",
            text="Awaiting first scene observation…",
            showarrow=False,
            font=dict(size=18, color="#888"),
        )

    # ── Audio sources strip (top of canvas) ──────────────────────────────────
    if scene.audio_sources:
        n = len(scene.audio_sources)
        start_x = 0.5 - (n - 1) * _AUDIO_X_SPACING / 2
        for i, src in enumerate(scene.audio_sources.values()):
            x = start_x + i * _AUDIO_X_SPACING
            label = f"{src.icon} {src.label}"
            if src.freq_hz:
                label += f"<br><b>{src.freq_hz} Hz</b>"
            fig.add_annotation(
                x=x, y=_AUDIO_BAR_Y, xref="x", yref="y",
                text=label,
                showarrow=False,
                font=dict(size=16, color="#111"),
                align="center",
            )

    # ── Canvas styling ───────────────────────────────────────────────────────
    fig.update_layout(
        title="🗺️  Grounded 2D World Map",
        xaxis=dict(range=[-0.05, 1.05], showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(range=[-0.05, 1.20], showgrid=False, showticklabels=False, zeroline=False,
                   scaleanchor="x", scaleratio=1),
        plot_bgcolor="#f5f0e6",
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=20),
        height=560,
        showlegend=False,
    )

    return fig
