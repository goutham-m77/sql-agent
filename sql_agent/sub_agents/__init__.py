"""
Sub-agents for the SQL Agent.

Each sub-agent is specialized for a particular task:
- SchemaAgent: For schema and table selection
- QueryAgent: For SQL generation and execution
- DiscrepancyAgent: For identifying data discrepancies
"""

from .schema_agent import SchemaAgent
from .query_agent import QueryAgent
from .discrepancy_agent import DiscrepancyAgent

__all__ = ["SchemaAgent", "QueryAgent", "DiscrepancyAgent"]
