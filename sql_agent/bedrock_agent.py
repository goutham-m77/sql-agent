"""
Amazon Bedrock integration for the SQL Agent.
"""
import os
from typing import Dict, Any, List, Optional
import logging
import json
import boto3
from botocore.exceptions import ClientError
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage

# Configure logging
logger = logging.getLogger(__name__)

# Default model to use (Claude 3 Sonnet - good balance of performance and cost for SQL tasks)
DEFAULT_MODEL = "anthropic.claude-3-sonnet-20240229-v1:0"


class BedrockAgent:
    """
    Agent for interacting with Amazon Bedrock models.
    
    This agent provides methods to generate SQL queries and analyze data
    using large language models from Amazon Bedrock.
    """
    
    def __init__(
        self,
        model_id: Optional[str] = None,
        region_name: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ):
        """
        Initialize the Bedrock agent.
        
        Args:
            model_id: Bedrock model ID to use
            region_name: AWS region name
            temperature: Temperature for generation (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
        """
        # Load configuration from environment if not provided
        self.model_id = model_id or os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL)
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        self.profile_name = None  # Not using AWS profiles
        
        # Model parameters
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize Bedrock client
        self._initialize_client()
        
        logger.info(f"Bedrock Agent initialized with model: {self.model_id}")
    
    def _initialize_client(self):
        """Initialize Bedrock client."""
        try:
            # Get AWS session token from environment if available
            session_token = os.getenv("AWS_SESSION_TOKEN")
            access_key = os.getenv("AWS_ACCESS_KEY_ID")
            secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            
            # Create client with credentials from environment
            if session_token:
                # Use session token if provided
                self.client = boto3.client(
                    "bedrock-runtime", 
                    region_name=self.region_name,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    aws_session_token=session_token
                )
            else:
                self.client = boto3.client(
                    "bedrock-runtime", 
                    region_name=self.region_name,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key
                )
            
            # Create LangChain wrapper for easier use
            self.llm = ChatBedrock(
                model_id=self.model_id,
                client=self.client,
                model_kwargs={
                    "temperature": self.temperature,
                    "max_tokens_to_sample": self.max_tokens
                }
            )
            
            # Test connection
            bedrock_client = boto3.client(
                "bedrock", 
                region_name=self.region_name,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                aws_session_token=session_token if session_token else None
            )
            models = bedrock_client.list_foundation_models()
            available_models = [model["modelId"] for model in models["modelSummaries"]]
            
            if self.model_id not in available_models:
                available_models_str = ", ".join(available_models)
                logger.warning(f"Model {self.model_id} not found. Available models: {available_models_str}")
                
                # If model not found, use Claude 3 Sonnet as fallback
                if "anthropic.claude-3-sonnet-20240229-v1:0" in available_models:
                    self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
                    logger.info(f"Falling back to {self.model_id}")
                    self._initialize_client()  # Reinitialize with new model
            
        except ClientError as e:
            logger.error(f"Bedrock client error: {e}")
            raise
    
    def generate_sql(
        self,
        user_query: str,
        schema_info: Dict[str, Any],
        examples: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate SQL query from natural language.
        
        Args:
            user_query: Natural language query
            schema_info: Database schema information
            examples: Optional examples of queries and corresponding SQL
            
        Returns:
            Generated SQL query string
        """
        # Prepare schema information as string
        schema_str = self._format_schema_info(schema_info)
        
        # Prepare examples if provided
        examples_str = ""
        if examples and len(examples) > 0:
            examples_str = "Here are some examples of similar queries:\n\n"
            for i, example in enumerate(examples, 1):
                examples_str += f"Example {i}:\n"
                examples_str += f"User query: {example.get('query', '')}\n"
                examples_str += f"SQL: {example.get('sql', '')}\n\n"
        
        # Construct the prompt
        prompt = f"""You are an expert Oracle SQL developer. Generate a valid Oracle SQL query to answer the following question:

USER QUERY: {user_query}

DATABASE SCHEMA:
{schema_str}

{examples_str}
Your task is to write a well-optimized Oracle SQL query that answers the user's question.
Consider using appropriate Oracle-specific features when beneficial.
Return ONLY the SQL query without any explanations, comments or backticks.
"""

        try:
            # Generate SQL using Bedrock
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            # Extract and clean SQL query from the response content
            sql_query = response.content
            
            # Remove markdown formatting if present
            if sql_query.startswith("```sql"):
                sql_query = sql_query.replace("```sql", "", 1)
                if sql_query.endswith("```"):
                    sql_query = sql_query[:-3]
            elif sql_query.startswith("```"):
                sql_query = sql_query.replace("```", "", 1) 
                if sql_query.endswith("```"):
                    sql_query = sql_query[:-3]
                    
            return sql_query.strip()
            
        except Exception as e:
            logger.error(f"Error generating SQL with Bedrock: {e}")
            # Return a simple query as fallback
            return f"SELECT 'Error generating query: {str(e)}' FROM dual"
    
    def analyze_discrepancies(
        self,
        query_result: Dict[str, Any],
        business_rules: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze query results for discrepancies based on business rules.
        
        Args:
            query_result: Results from database query
            business_rules: Business rules for discrepancy detection
            
        Returns:
            List of identified discrepancies
        """
        # Skip if no query results
        if not query_result or "data" not in query_result or not query_result["data"]:
            return []
        
        # Prepare data and rules
        data = json.dumps(query_result["data"][:20])  # Limit to first 20 rows for prompt size
        rules_str = json.dumps(business_rules)
        
        # Construct the prompt
        prompt = f"""You are a data analyst examining database query results for discrepancies.

DATA (first 20 rows):
{data}

BUSINESS RULES:
{rules_str}

Analyze the data for discrepancies based on the business rules.
Return a JSON array of discrepancies, where each discrepancy has these fields:
- type: The type of discrepancy (e.g., "null_value", "inconsistent_data", "business_rule_violation")
- severity: The severity level ("low", "medium", "high")
- message: A clear message describing the discrepancy
- row_indices: Array of row indices where the discrepancy was found (0-based)
- fields: Array of field names involved in the discrepancy

Only return the JSON array without any explanation or markdown formatting.
If no discrepancies are found, return an empty array [].
"""

        try:
            # Generate analysis using Bedrock
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            # Extract and parse JSON
            discrepancies = []
            
            # Clean up response
            json_str = response.content
            
            # Remove markdown formatting if present
            if json_str.startswith("```json"):
                json_str = json_str.replace("```json", "", 1)
                if json_str.endswith("```"):
                    json_str = json_str[:-3]
            elif json_str.startswith("```"):
                json_str = json_str.replace("```", "", 1) 
                if json_str.endswith("```"):
                    json_str = json_str[:-3]
            
            # Parse JSON
            try:
                discrepancies = json.loads(json_str)
                if not isinstance(discrepancies, list):
                    discrepancies = []
            except json.JSONDecodeError:
                logger.error(f"Failed to parse discrepancy analysis: {json_str}")
                discrepancies = []
            
            return discrepancies
            
        except Exception as e:
            logger.error(f"Error analyzing discrepancies with Bedrock: {e}")
            return []
    
    def _format_schema_info(self, schema_info: Dict[str, Any]) -> str:
        """Format schema information for the prompt."""
        schema_str = ""
        
        selected_schema = schema_info.get("selected_schema", "")
        if selected_schema:
            schema_str += f"Schema: {selected_schema}\n\n"
        
        table_columns = schema_info.get("table_columns", {})
        for table, columns in table_columns.items():
            schema_str += f"Table: {table}\n"
            schema_str += f"Columns: {', '.join(columns)}\n\n"
        
        return schema_str
