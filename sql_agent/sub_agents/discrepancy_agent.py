"""
Discrepancy agent for identifying data inconsistencies in Oracle databases.
"""
from typing import Dict, List, Any, Optional, Callable
import logging
import oracledb

# Configure logging
logger = logging.getLogger(__name__)


class DiscrepancyAgent:
    """
    Agent responsible for identifying data discrepancies.
    
    This agent applies business rules to check for inconsistencies
    in database query results.
    """
    
    def __init__(self, connection, memory, bedrock_agent=None):
        """
        Initialize the discrepancy agent.
        
        Args:
            connection: Oracle DB connection
            memory: Memory module for context
            bedrock_agent: Amazon Bedrock agent for AI capabilities
        """
        self.connection = connection
        self.memory = memory
        self.bedrock_agent = bedrock_agent
        self.business_rules = {}
        
        logger.info("Discrepancy Agent initialized for Oracle")
    
    def set_business_rules(self, rules: Dict[str, Any]):
        """
        Set business logic rules for discrepancy detection.
        
        Args:
            rules: Dictionary containing business logic rules
        """
        self.business_rules = rules
        logger.info(f"Set {len(rules)} business rules")
    
    def check_discrepancies(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for discrepancies in query results based on business rules.
        
        Args:
            context: Context from previous steps
            
        Returns:
            List of identified discrepancies
        """
        query_result = context.get("query_result", {})
        schema_info = context.get("schema_info", {})
        
        discrepancies = []
        
        # Skip if no query results
        if not query_result:
            return discrepancies
        
        # Get data from query results
        data = query_result.get("data", [])
        if not data:
            return discrepancies
        
        # Use Bedrock for AI-powered discrepancy detection if available
        if self.bedrock_agent and self.business_rules:
            ai_discrepancies = self.bedrock_agent.analyze_discrepancies(
                query_result,
                self.business_rules
            )
            discrepancies.extend(ai_discrepancies)
        
        # Apply generic consistency checks
        generic_discrepancies = self._apply_generic_checks(data, schema_info)
        discrepancies.extend(generic_discrepancies)
        
        # Apply business-specific rules with SQL queries
        business_discrepancies = self._apply_business_rules(data, schema_info)
        discrepancies.extend(business_discrepancies)
        
        # Store discrepancies in memory
        if discrepancies:
            self.memory.add("discrepancies", discrepancies)
            
        return discrepancies
    
    def _apply_generic_checks(self, data: List[Dict[str, Any]], schema_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply generic consistency checks to the data.
        
        Args:
            data: Query result data
            schema_info: Schema information
            
        Returns:
            List of identified discrepancies
        """
        discrepancies = []
        
        # Check for null values in important fields
        for idx, row in enumerate(data):
            for field, value in row.items():
                # Skip non-critical fields
                if field.lower() in ["id", "created_at", "updated_at", "notes", "description"]:
                    continue
                    
                if value is None:
                    discrepancies.append({
                        "type": "null_value",
                        "severity": "low",
                        "message": f"Null value detected in field '{field}' at row {idx + 1}",
                        "row_indices": [idx],
                        "fields": [field]
                    })
        
        # Check for duplicates in unique fields
        seen_values = {}
        primary_fields = ["id", "code", "key"]
        
        for field in primary_fields:
            if data and field in data[0].keys():
                seen_values[field] = {}
                
                for idx, row in enumerate(data):
                    value = row.get(field)
                    if value in seen_values[field]:
                        discrepancies.append({
                            "type": "duplicate_value",
                            "severity": "high",
                            "message": f"Duplicate value '{value}' in field '{field}' at rows {seen_values[field][value] + 1} and {idx + 1}",
                            "row_indices": [seen_values[field][value], idx],
                            "fields": [field],
                            "value": value
                        })
                    else:
                        seen_values[field][value] = idx
        
        return discrepancies
    
    def _apply_business_rules(self, data: List[Dict[str, Any]], schema_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply business-specific rules to the data.
        
        Args:
            data: Query result data
            schema_info: Schema information
            
        Returns:
            List of identified discrepancies
        """
        discrepancies = []
        
        # Skip if no business rules
        if not self.business_rules:
            return discrepancies
        
        # Apply each business rule
        for rule_name, rule in self.business_rules.items():
            if callable(getattr(self, f"_check_{rule_name}", None)):
                rule_func = getattr(self, f"_check_{rule_name}")
                rule_discrepancies = rule_func(data, rule)
                discrepancies.extend(rule_discrepancies)
            elif "check_function" in rule and callable(rule["check_function"]):
                # Rule provides its own check function
                rule_discrepancies = rule["check_function"](data)
                discrepancies.extend(rule_discrepancies)
            elif "sql_query" in rule:
                # Rule provides a SQL query to check discrepancies
                rule_discrepancies = self._execute_rule_query(rule)
                discrepancies.extend(rule_discrepancies)
        
        return discrepancies
    
    def _execute_rule_query(self, rule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a SQL query to check for discrepancies."""
        discrepancies = []
        
        sql_query = rule.get("sql_query")
        if not sql_query:
            return discrepancies
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql_query)
            
            # Get column names
            columns = [col[0] for col in cursor.description] if cursor.description else []
            
            # Process rows
            rows = []
            for row in cursor.fetchall():
                rows.append(dict(zip(columns, row)))
            
            if rows:
                for idx, row in enumerate(rows):
                    discrepancies.append({
                        "type": rule.get("type", "business_rule"),
                        "severity": rule.get("severity", "medium"),
                        "message": rule.get("message", f"Business rule '{rule.get('name', 'unnamed')}' violated"),
                        "rule_name": rule.get("name", "unnamed"),
                        "details": row
                    })
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"Error executing rule query: {e}")
        
        return discrepancies
    
    # Example built-in check methods that can be extended
    
    def _check_price_consistency(self, data: List[Dict[str, Any]], rule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for price consistency across related products."""
        discrepancies = []
        
        # Implementation would depend on the specific business logic
        # This is just an example template
        
        return discrepancies
    
    def _check_inventory_balance(self, data: List[Dict[str, Any]], rule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check that inventory transactions balance correctly."""
        discrepancies = []
        
        # Implementation would depend on the specific business logic
        # This is just an example template
        
        return discrepancies
