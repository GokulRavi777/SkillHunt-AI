"""Dedicated LangGraph Studio Entry Point for VANI 2.0.

Provides a clean, standalone import of the compiled LangGraph workflow without triggering
LiveKit voice runners, external audio processing, or WebSocket listeners.

In LangGraph Studio / Server mode, persistence is managed natively by the LangGraph platform runtime,
so the graph is exposed cleanly compiled without an external in-memory checkpointer conflict.
"""
from vani.graph.workflow import create_interview_graph

# Expose the compiled graph for LangGraph Studio inspection, visualization and tracing
vani_graph = create_interview_graph().compile()

__all__ = ["vani_graph", "create_interview_graph"]
