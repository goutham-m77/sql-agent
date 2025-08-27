"""
Schema agent for selecting appropriate Oracle schemas and tables.
"""
from typing import Dict, List, Any, Optional
import logging
import re
import oracledb

# Configure logging
logger = logging.getLogger(__name__)


class SchemaAgent:
    """
    Agent responsible for Oracle schema and table selection.
    
    This agent analyzes the user query to determine the most appropriate
    schema and tables to use for the query.
    """
    
    def __init__(self, connection, memory):
        """
        Initialize the schema agent.
        
        Args:
            connection: Oracle DB connection
            memory: Memory module for context
        """
        self.connection = connection
        self.memory = memory
        
        # Cache schema information
        self.schemas = self._get_schemas()
        self.schema_cache = self._build_schema_cache()
        
        logger.info("Schema Agent initialized for Oracle")
    
    def _get_schemas(self) -> List[str]:
        """Get available schemas (users) in Oracle."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT username 
                FROM all_users 
                WHERE username NOT IN ('SYS', 'SYSTEM', 'DBSNMP', 'OUTLN')
                ORDER BY username
            """)
            schemas = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return schemas
        except Exception as e:
            logger.error(f"Error getting schemas: {e}")
            return []
    
    def _build_schema_cache(self) -> Dict[str, Dict[str, List[str]]]:
        """Build a cache of schema and table information."""
        schema_info = {}
        
        try:
            cursor = self.connection.cursor()
            
            for schema in self.schemas:
                table_dict = {}
                
                # Get tables for this schema
                cursor.execute(f"""
                    SELECT table_name 
                    FROM all_tables 
                    WHERE owner = '{schema}'
                    ORDER BY table_name
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                # Get column info for each table
                for table in tables:
                    cursor.execute(f"""
                        SELECT column_name
                        FROM all_tab_columns
                        WHERE owner = '{schema}' AND table_name = '{table}'
                        ORDER BY column_id
                    """)
                    columns = [row[0] for row in cursor.fetchall()]
                    table_dict[table] = columns
                
                schema_info[schema] = table_dict
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"Error building schema cache: {e}")
        
        return schema_info
    
    def get_schema_info(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine the most appropriate schema and tables for a query.
        
        Args:
            query: Natural language query from the user
            context: Context from previous steps
            
        Returns:
            Dictionary with schema information
        """
        logger.info(f"Determining schema for query: {query}")
        
        # Check if schema or tables are explicitly mentioned
        suggested_schema = context.get("suggested_schema") or self._extract_schema_from_query(query)
        suggested_tables = context.get("suggested_tables") or self._extract_tables_from_query(query)
        
        # If no schema is suggested, use the first available one
        if not suggested_schema and self.schemas:
            suggested_schema = self.schemas[0]
            logger.info(f"No schema specified, using default: {suggested_schema}")
        
        # If no tables are suggested, infer from query
        if not suggested_tables:
            suggested_tables = self._infer_tables_from_query(query, suggested_schema)
        
        result = {
            "available_schemas": self.schemas,
            "selected_schema": suggested_schema,
            "selected_tables": suggested_tables,
            "table_columns": {}
        }
        
        # Add column information for selected tables
        for table in suggested_tables:
            if suggested_schema in self.schema_cache and table in self.schema_cache[suggested_schema]:
                result["table_columns"][table] = self.schema_cache[suggested_schema][table]
        
        # Store in memory for future reference
        self.memory.add("schema_selections", result)
        
        return result
    
    def _extract_schema_from_query(self, query: str) -> Optional[str]:
        """Extract schema name from the query."""
        query_lower = query.lower()
        
        # Check for explicit schema references
        schema_patterns = [
            r"in schema ['\"]?([a-zA-Z0-9_]+)['\"]?",
            r"from schema ['\"]?([a-zA-Z0-9_]+)['\"]?",
            r"database ['\"]?([a-zA-Z0-9_]+)['\"]?"
        ]
        
        for pattern in schema_patterns:
            match = re.search(pattern, query_lower)
            if match:
                schema_name = match.group(1)
                if schema_name in self.schemas:
                    return schema_name
        
        return None
    
    def _extract_tables_from_query(self, query: str) -> List[str]:
        """Extract table names from the query."""
        query_lower = query.lower()
        tables = []
        
        # Check for explicit table references
        table_patterns = [
            r"from ['\"]?([a-zA-Z0-9_]+)['\"]?",
            r"table[s]? ['\"]?([a-zA-Z0-9_]+)['\"]?",
            r"in ['\"]?([a-zA-Z0-9_]+)['\"]? table"
        ]
        
        for pattern in table_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                table_name = match.group(1)
                # Verify the table exists in at least one schema
                for schema in self.schemas:
                    if schema in self.schema_cache and table_name in self.schema_cache[schema]:
                        tables.append(table_name)
                        break
        
        return tables
    
    def _infer_tables_from_query(self, query: str, schema: Optional[str]) -> List[str]:
        """
        Infer relevant tables based on query keywords.
        
        Args:
            query: The user's query
            schema: The selected schema
            
        Returns:
            List of inferred table names
        """
        if not schema or schema not in self.schema_cache:
            return []
        
        # Extract key nouns from the query that might correspond to tables
        query_lower = query.lower()
        words = set(re.findall(r'\b[a-zA-Z0-9_]{3,}\b', query_lower))
        
        # Look for singular and plural forms of table names
        available_tables = set(self.schema_cache[schema].keys())
        
        # Score each table based on word overlap
        table_scores = {}
        for table in available_tables:
            table_lower = table.lower()
            
            # Check for exact match
            if table_lower in words:
                table_scores[table] = 1.0
                continue
                
            # Check for singular/plural forms
            singular = table_lower[:-1] if table_lower.endswith('s') else table_lower
            plural = f"{table_lower}s" if not table_lower.endswith('s') else table_lower
            
            if singular in words or plural in words:
                table_scores[table] = 0.9
                continue
                
            # Check for partial matches (table name is part of a word in query)
            for word in words:
                if table_lower in word or word in table_lower:
                    similarity = len(word) / max(len(word), len(table_lower))
                    table_scores[table] = max(table_scores.get(table, 0), similarity * 0.8)
        
        # Sort by score and take top results
        sorted_tables = sorted([(score, table) for table, score in table_scores.items()], reverse=True)
        
        # Return top tables with scores above threshold
        return [table for score, table in sorted_tables if score >= 0.5][:3]
