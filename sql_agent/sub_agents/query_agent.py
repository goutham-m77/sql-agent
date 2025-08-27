"""
Query agent for generating and executing Oracle SQL queries.
"""
from typing import Dict, List, Any, Optional, Union
import logging
import oracledb
import re
import os
from ..utils.db_utils import format_oracle_results

# Configure logging
logger = logging.getLogger(__name__)


class QueryAgent:
    """
    Agent responsible for generating and executing Oracle SQL queries.
    
    This agent translates natural language queries into SQL and
    executes them against the Oracle database.
    """
    
    def __init__(self, connection, memory, bedrock_agent=None):
        """
        Initialize the query agent.
        
        Args:
            connection: Oracle DB connection
            memory: Memory module for context
            bedrock_agent: Amazon Bedrock agent for AI capabilities
        """
        self.connection = connection
        self.memory = memory
        self.bedrock_agent = bedrock_agent
        
        logger.info("Query Agent initialized for Oracle")
    
    def execute_query(
        self, 
        user_query: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate and execute SQL query based on user's natural language query.
        
        Args:
            user_query: Natural language query from the user
            context: Context from previous steps
            
        Returns:
            Dictionary with query results
        """
        logger.info(f"Executing query: {user_query}")
        
        # Get schema information from context
        schema_info = context.get("schema_info", {})
        schema_name = schema_info.get("selected_schema")
        tables = schema_info.get("selected_tables", [])
        table_columns = schema_info.get("table_columns", {})
        
        # Generate SQL query
        sql_query = self._generate_sql_query(user_query, schema_info)
        logger.info(f"Generated SQL: {sql_query}")
        
        # Execute SQL query
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql_query)
            
            formatted_result = format_oracle_results(cursor)
            
            # Add the SQL query to the result
            formatted_result["sql_query"] = sql_query
            
            # Store in memory for future reference
            self.memory.add(
                "executed_queries", 
                {"user_query": user_query, "sql_query": sql_query}
            )
            
            cursor.close()
            return formatted_result
                
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return {
                "error": str(e),
                "sql_query": sql_query
            }
    
    def _generate_sql_query(
        self, 
        user_query: str,
        schema_info: Dict[str, Any]
    ) -> str:
        """
        Generate SQL query from natural language.
        
        Args:
            user_query: Natural language query
            schema_info: Schema information dictionary
            
        Returns:
            SQL query string
        """
        if self.bedrock_agent:
            # Get previous queries for examples
            previous_queries = self.memory.get("executed_queries", n=3)
            examples = []
            
            for item in previous_queries:
                if "content" in item and "user_query" in item["content"] and "sql_query" in item["content"]:
                    examples.append({
                        "query": item["content"]["user_query"],
                        "sql": item["content"]["sql_query"]
                    })
            
            # Generate SQL using Bedrock
            return self.bedrock_agent.generate_sql(user_query, schema_info, examples)
        else:
            return self._generate_sql_with_rules(user_query, schema_info)
    
    def _generate_sql_with_rules(
        self, 
        user_query: str,
        schema_info: Dict[str, Any]
    ) -> str:
        """
        Generate SQL using rule-based approach (fallback).
        
        This is a simple implementation that handles basic queries.
        For complex queries, Bedrock integration is recommended.
        """
        user_query = user_query.lower()
        
        # Extract schema and tables from schema_info
        schema_name = schema_info.get("selected_schema")
        tables = schema_info.get("selected_tables", [])
        table_columns = schema_info.get("table_columns", {})
        
        # Default to SELECT * if no tables
        if not tables:
            return f"SELECT 'No tables selected' FROM dual"
        
        # Use the first table if multiple are available
        primary_table = tables[0]
        columns = table_columns.get(primary_table, ["*"])
        
        # Handle different query types
        if any(word in user_query for word in ["count", "how many"]):
            return f"SELECT COUNT(*) FROM {schema_name}.{primary_table}"
        
        elif any(word in user_query for word in ["average", "avg", "mean"]):
            # Find a numeric column to average
            numeric_column = next(
                (col for col in columns if any(
                    hint in col.lower() for hint in ["amount", "price", "value", "num", "total", "qty", "quantity"]
                )),
                None
            )
            
            if numeric_column:
                return f"SELECT AVG({numeric_column}) FROM {schema_name}.{primary_table}"
            else:
                return f"SELECT * FROM {schema_name}.{primary_table} WHERE ROWNUM <= 10"
        
        elif "group by" in user_query:
            # Find a category column to group by
            category_column = next(
                (col for col in columns if any(
                    hint in col.lower() for hint in ["category", "type", "status", "group", "class", "department"]
                )),
                None
            )
            
            numeric_column = next(
                (col for col in columns if any(
                    hint in col.lower() for hint in ["amount", "price", "value", "num", "total", "qty", "quantity"]
                )),
                None
            )
            
            if category_column and numeric_column:
                return f"SELECT {category_column}, SUM({numeric_column}) FROM {schema_name}.{primary_table} GROUP BY {category_column}"
            else:
                return f"SELECT * FROM {schema_name}.{primary_table} WHERE ROWNUM <= 10"
        
        else:
            # Default to a simple SELECT
            limit = "WHERE ROWNUM <= 100" if "all" not in user_query else ""
            return f"SELECT * FROM {schema_name}.{primary_table} {limit}"
    
    def _generate_sql_with_rules(
        self, 
        user_query: str,
        schema_name: Optional[str],
        tables: List[str],
        table_columns: Dict[str, List[str]]
    ) -> str:
        """
        Generate SQL using rule-based approach (fallback).
        
        This is a simple implementation that handles basic queries.
        For complex queries, OpenAI integration is recommended.
        """
        user_query = user_query.lower()
        
        # Default to SELECT * if no tables
        if not tables:
            return f"SELECT 'No tables selected' AS message"
        
        # Use the first table if multiple are available
        primary_table = tables[0]
        columns = table_columns.get(primary_table, ["*"])
        
        # Handle different query types
        if any(word in user_query for word in ["count", "how many"]):
            return f"SELECT COUNT(*) FROM {schema_name}.{primary_table}"
        
        elif any(word in user_query for word in ["average", "avg", "mean"]):
            # Find a numeric column to average
            numeric_column = next(
                (col for col in columns if any(
                    hint in col.lower() for hint in ["amount", "price", "value", "num", "total", "qty", "quantity"]
                )),
                None
            )
            
            if numeric_column:
                return f"SELECT AVG({numeric_column}) FROM {schema_name}.{primary_table}"
            else:
                return f"SELECT * FROM {schema_name}.{primary_table} LIMIT 10"
        
        elif "group by" in user_query:
            # Find a category column to group by
            category_column = next(
                (col for col in columns if any(
                    hint in col.lower() for hint in ["category", "type", "status", "group", "class", "department"]
                )),
                None
            )
            
            numeric_column = next(
                (col for col in columns if any(
                    hint in col.lower() for hint in ["amount", "price", "value", "num", "total", "qty", "quantity"]
                )),
                None
            )
            
            if category_column and numeric_column:
                return f"SELECT {category_column}, SUM({numeric_column}) FROM {schema_name}.{primary_table} GROUP BY {category_column}"
            else:
                return f"SELECT * FROM {schema_name}.{primary_table} LIMIT 10"
        
        else:
            # Default to a simple SELECT
            limit = "LIMIT 100" if "all" not in user_query else ""
            return f"SELECT * FROM {schema_name}.{primary_table} {limit}"
