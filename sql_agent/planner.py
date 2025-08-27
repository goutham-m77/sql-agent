"""
Planner module for SQLAgent to break down complex queries into steps.
"""
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, field
import json
import re

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class PlanStep:
    """A single step in the execution plan."""
    agent: str  # Name of the agent responsible for this step
    action: str  # Action to perform
    description: str  # Description of the step
    params: Dict[str, Any] = field(default_factory=dict)  # Parameters for the step


@dataclass
class Plan:
    """A plan for executing a database query."""
    query: str  # Original user query
    steps: List[PlanStep] = field(default_factory=list)  # Steps to execute
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the plan to a dictionary."""
        return {
            "query": self.query,
            "steps": [
                {
                    "agent": step.agent,
                    "action": step.action,
                    "description": step.description,
                    "params": step.params
                }
                for step in self.steps
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Plan':
        """Create a plan from a dictionary."""
        plan = cls(query=data["query"])
        for step_data in data["steps"]:
            step = PlanStep(
                agent=step_data["agent"],
                action=step_data["action"],
                description=step_data["description"],
                params=step_data["params"]
            )
            plan.steps.append(step)
        return plan


class Planner:
    """
    Planning module for SQL Agent to break down complex queries into steps.
    
    This module creates execution plans that coordinate multiple agents for query processing.
    """
    
    def __init__(self, max_depth: int = 5):
        """
        Initialize the planner.
        
        Args:
            max_depth: Maximum depth for planning recursion
        """
        self.max_depth = max_depth
        
        # Define templates for planning
        self._define_templates()
        
        logger.info("Planner initialized")
    
    def _define_templates(self):
        """Define planning templates."""
        self.templates = {
            "standard_query": [
                PlanStep(
                    agent="schema",
                    action="get_schema_info",
                    description="Determine which schema and tables to use"
                ),
                PlanStep(
                    agent="query",
                    action="execute_query",
                    description="Generate and execute SQL query"
                )
            ],
            "query_with_discrepancy": [
                PlanStep(
                    agent="schema",
                    action="get_schema_info",
                    description="Determine which schema and tables to use"
                ),
                PlanStep(
                    agent="query",
                    action="execute_query",
                    description="Generate and execute SQL query"
                ),
                PlanStep(
                    agent="discrepancy",
                    action="check_discrepancies",
                    description="Check for discrepancies in the data"
                )
            ]
        }
    
    def create_plan(self, query: str) -> Plan:
        """
        Create an execution plan for the given query.
        
        Args:
            query: Natural language query from the user
            
        Returns:
            Plan object with steps to execute
        """
        # Analyze the query to determine the appropriate template
        if self._query_needs_discrepancy_check(query):
            steps = self._copy_template("query_with_discrepancy")
        else:
            steps = self._copy_template("standard_query")
        
        # Customize the plan based on the query
        steps = self._customize_plan(steps, query)
        
        return Plan(query=query, steps=steps)
    
    def _copy_template(self, template_name: str) -> List[PlanStep]:
        """Create a copy of a template."""
        template = self.templates.get(template_name, [])
        return [
            PlanStep(
                agent=step.agent,
                action=step.action,
                description=step.description,
                params=step.params.copy()
            )
            for step in template
        ]
    
    def _customize_plan(self, steps: List[PlanStep], query: str) -> List[PlanStep]:
        """Customize the plan based on the query."""
        query_lower = query.lower()
        
        # Check if the query is about specific tables
        table_match = re.search(r"(table|tables) (\w+)", query_lower)
        if table_match:
            table_name = table_match.group(2)
            for step in steps:
                if step.agent == "schema":
                    step.params["suggested_tables"] = [table_name]
        
        # Check if the query is about a specific schema
        schema_match = re.search(r"(schema|database) (\w+)", query_lower)
        if schema_match:
            schema_name = schema_match.group(2)
            for step in steps:
                if step.agent == "schema":
                    step.params["suggested_schema"] = schema_name
        
        return steps
    
    def _query_needs_discrepancy_check(self, query: str) -> bool:
        """Determine if the query needs a discrepancy check."""
        discrepancy_keywords = [
            "discrepancy", "discrepancies", "inconsistency", "inconsistencies",
            "error", "errors", "mismatch", "mismatches", "wrong", "incorrect",
            "validate", "validation", "verify", "verification", "check"
        ]
        
        query_lower = query.lower()
        
        return any(keyword in query_lower for keyword in discrepancy_keywords)
