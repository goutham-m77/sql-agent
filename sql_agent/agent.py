"""
SQLAgent - A deep agent for Oracle database interaction and discrepancy detection.
"""
import os
from typing import Dict, List, Any, Optional, Union
import logging

from dotenv import load_dotenv
import oracledb

from .memory import Memory
from .planner import Planner
from .sub_agents.schema_agent import SchemaAgent
from .sub_agents.query_agent import QueryAgent
from .sub_agents.discrepancy_agent import DiscrepancyAgent
from .utils.db_utils import get_oracle_connection_params, create_oracle_connection
from .bedrock_agent import BedrockAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class SQLAgent:
    """
    A deep agent for intelligent Oracle database interaction.
    
    This agent can:
    - Process natural language queries about Oracle databases
    - Select appropriate schemas and tables
    - Retain memory of past interactions
    - Detect discrepancies based on business logic
    - Use planning to break down complex queries
    - Leverage Amazon Bedrock for AI capabilities
    """
    
    def __init__(
        self,
        connection_params: Optional[Dict[str, Any]] = None,
        memory_ttl: Optional[int] = None,
        max_planning_depth: Optional[int] = None,
        enable_sub_agents: Optional[bool] = None,
        bedrock_model_id: Optional[str] = None,
        bedrock_region: Optional[str] = None,
    ):
        """
        Initialize the SQL Agent.
        
        Args:
            connection_params: Oracle connection parameters. If None, will be loaded from env vars
            memory_ttl: Time-to-live for memory entries in seconds
            max_planning_depth: Maximum depth for planning recursion
            enable_sub_agents: Whether to use sub-agents
            bedrock_model_id: Amazon Bedrock model ID to use
            bedrock_region: AWS region for Bedrock
        """
        # Load configuration from environment if not provided
        self.connection_params = connection_params or get_oracle_connection_params()
        self.memory_ttl = memory_ttl or int(os.getenv("MEMORY_TTL", "3600"))
        self.max_planning_depth = max_planning_depth or int(os.getenv("MAX_PLANNING_DEPTH", "5"))
        self.enable_sub_agents = enable_sub_agents if enable_sub_agents is not None else \
                                os.getenv("ENABLE_SUB_AGENTS", "true").lower() == "true"
        self.bedrock_model_id = bedrock_model_id
        self.bedrock_region = bedrock_region
        
        # Initialize components
        self._initialize_components()
        
        logger.info("SQL Agent initialized for Oracle database")
    
    def _initialize_components(self):
        """Initialize the agent's components."""
        # Create database connection
        try:
            self.connection = create_oracle_connection(self.connection_params)
            
            # Get schemas (users in Oracle)
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT username 
                FROM all_users 
                WHERE username NOT IN ('SYS', 'SYSTEM', 'DBSNMP', 'OUTLN')
                ORDER BY username
            """)
            self.schemas = [row[0] for row in cursor.fetchall()]
            cursor.close()
            
            logger.info(f"Connected to Oracle database. Available schemas: {self.schemas}")
        except Exception as e:
            logger.error(f"Oracle database connection error: {e}")
            raise
        
        # Initialize memory
        self.memory = Memory(ttl=self.memory_ttl)
        
        # Initialize planner
        self.planner = Planner(max_depth=self.max_planning_depth)
        
        # Initialize Amazon Bedrock agent
        self.bedrock_agent = BedrockAgent(
            model_id=self.bedrock_model_id,
            region_name=self.bedrock_region
        )
        
        # Initialize sub-agents if enabled
        if self.enable_sub_agents:
            self.schema_agent = SchemaAgent(connection=self.connection, memory=self.memory)
            self.query_agent = QueryAgent(
                connection=self.connection, 
                memory=self.memory,
                bedrock_agent=self.bedrock_agent
            )
            self.discrepancy_agent = DiscrepancyAgent(
                connection=self.connection, 
                memory=self.memory,
                bedrock_agent=self.bedrock_agent
            )
    
    def query(self, user_query: str) -> Dict[str, Any]:
        """
        Process a natural language query and return results.
        
        Args:
            user_query: The natural language query from the user
            
        Returns:
            Dictionary containing results and metadata
        """
        logger.info(f"Received query: {user_query}")
        
        # Store query in memory
        self.memory.add("user_queries", user_query)
        
        # Create a plan for handling the query
        plan = self.planner.create_plan(user_query)
        logger.info(f"Created plan with {len(plan.steps)} steps")
        
        # Execute the plan
        result = self._execute_plan(plan, user_query)
        
        return result
    
    def _execute_plan(self, plan, user_query):
        """Execute the steps in the plan and return results."""
        context = {"user_query": user_query}
        
        for step in plan.steps:
            if step.agent == "schema":
                # Determine which schema and tables to use
                schema_info = self.schema_agent.get_schema_info(user_query, context)
                context["schema_info"] = schema_info
            
            elif step.agent == "query":
                # Generate and execute SQL query
                query_result = self.query_agent.execute_query(user_query, context)
                context["query_result"] = query_result
            
            elif step.agent == "discrepancy":
                # Check for discrepancies in the data
                discrepancies = self.discrepancy_agent.check_discrepancies(context)
                context["discrepancies"] = discrepancies
        
        # Store the final context in memory
        self.memory.add("query_contexts", context)
        
        return {
            "result": context.get("query_result", {}),
            "discrepancies": context.get("discrepancies", []),
            "schema_used": context.get("schema_info", {}).get("selected_schema"),
            "tables_used": context.get("schema_info", {}).get("selected_tables", []),
            "plan": plan.to_dict(),
        }
    
    def set_business_logic(self, rules: Dict[str, Any]):
        """
        Set business logic rules for discrepancy detection.
        
        Args:
            rules: Dictionary containing business logic rules
        """
        if hasattr(self, "discrepancy_agent"):
            self.discrepancy_agent.set_business_rules(rules)
            logger.info("Business logic rules updated")
        else:
            logger.warning("Discrepancy agent not initialized. Enable sub-agents to use this feature.")
    
    def get_schema_info(self) -> Dict[str, Any]:
        """
        Get information about the database schema.
        
        Returns:
            Dictionary with schema information
        """
        schema_info = {}
        
        try:
            cursor = self.connection.cursor()
            
            # Get all schemas (users)
            for schema in self.schemas:
                # Get tables for this schema
                cursor.execute(f"""
                    SELECT table_name 
                    FROM all_tables 
                    WHERE owner = '{schema}'
                    ORDER BY table_name
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                # Get column info for each table
                table_info = {}
                for table in tables:
                    cursor.execute(f"""
                        SELECT column_name
                        FROM all_tab_columns
                        WHERE owner = '{schema}' AND table_name = '{table}'
                        ORDER BY column_id
                    """)
                    columns = [row[0] for row in cursor.fetchall()]
                    table_info[table] = columns
                
                schema_info[schema] = table_info
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"Error getting schema info: {e}")
        
        return schema_info
