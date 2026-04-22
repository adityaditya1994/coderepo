"""
Agent I/O Contracts — Pydantic models defining the data contract
between each pair of adjacent agents in the graph.

Each model maps 1:1 to slices of AgentState and provides
to_state() / from_state() adapters for serialization.

Per-agent contract files live under contracts/<agent>.py.
This module re-exports all models for backward compatibility.
"""

# Supervisor
from contracts.supervisor import SupervisorInput, SupervisorOutput  # noqa: F401

# Discovery
from contracts.discovery import DiscoveryInput, DiscoveryOutput  # noqa: F401

# Schema Retriever
from contracts.schema_retriever import SchemaRetrieverInput, SchemaRetrieverOutput  # noqa: F401

# Query Planner
from contracts.query_planner import QueryPlannerInput, QueryPlannerOutput  # noqa: F401

# SQL Generator
from contracts.sql_generator import SqlGeneratorInput, SqlGeneratorOutput  # noqa: F401

# Executor
from contracts.executor import ExecutorInput, ExecutorOutput  # noqa: F401

# SQL Fixer
from contracts.sql_fixer import SqlFixerInput, SqlFixerOutput  # noqa: F401

# Validation Council
from contracts.validation_council import ValidationCouncilInput, ValidationCouncilOutput  # noqa: F401

# Summarizer
from contracts.summarizer import SummarizerInput, SummarizerOutput  # noqa: F401

# Human Handoff
from contracts.human_handoff import HumanHandoffInput, HumanHandoffOutput  # noqa: F401

# Memory Writer
from contracts.memory_writer import MemoryWriterInput, MemoryWriterOutput  # noqa: F401
