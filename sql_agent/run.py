"""
Example script to demonstrate the SQL Agent with Oracle DB and Amazon Bedrock.
"""
import os
import logging
from dotenv import load_dotenv
import json

from sql_agent import SQLAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def set_sample_business_rules(agent):
    """Set some sample business rules for demonstration."""
    business_rules = {
        "price_consistency": {
            "name": "Price Consistency",
            "description": "Ensure prices are consistent across related products",
            "severity": "medium",
            "sql_query": """
                SELECT p1.product_id AS product1_id, p1.product_name AS product1_name, 
                       p1.price AS product1_price,
                       p2.product_id AS product2_id, p2.product_name AS product2_name, 
                       p2.price AS product2_price
                FROM products p1
                JOIN products p2 ON p1.category_id = p2.category_id AND p1.product_id != p2.product_id
                WHERE ABS(p1.price - p2.price) / NULLIF(p1.price, 0) > 0.5
                AND ROWNUM <= 10
            """,
            "message": "Products in the same category have significant price differences"
        },
        "inventory_balance": {
            "name": "Inventory Balance",
            "description": "Check that inventory transactions balance correctly",
            "severity": "high",
            "sql_query": """
                SELECT product_id, 
                       SUM(CASE WHEN transaction_type = 'IN' THEN quantity ELSE -quantity END) AS balance
                FROM inventory_transactions
                GROUP BY product_id
                HAVING SUM(CASE WHEN transaction_type = 'IN' THEN quantity ELSE -quantity END) != 0
                AND ROWNUM <= 10
            """,
            "message": "Inventory transactions do not balance for some products"
        }
    }
    
    agent.set_business_logic(business_rules)
    logger.info("Set sample business rules")


def main():
    """Run the example."""
    try:
        # Initialize the SQL Agent
        # You can provide connection parameters directly here, or use environment variables
        agent = SQLAgent(
            bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"),
            bedrock_region=os.getenv("AWS_REGION", "us-east-1")
        )
        logger.info("Initialized SQL Agent for Oracle with Amazon Bedrock")
        
        # Set sample business rules
        set_sample_business_rules(agent)
        
        while True:
            # Get user input
            user_query = input("\nEnter your database query (or 'exit' to quit): ")
            
            if user_query.lower() in ['exit', 'quit']:
                break
            
            # Process the query
            result = agent.query(user_query)
            
            # Print the result
            print("\n=== Query Results ===")
            print(f"SQL Query: {result.get('result', {}).get('sql_query', 'N/A')}")
            
            if 'error' in result.get('result', {}):
                print(f"Error: {result['result']['error']}")
            else:
                print(f"\nSchema: {result.get('schema_used', 'N/A')}")
                print(f"Tables: {', '.join(result.get('tables_used', []))}")
                
                if 'data' in result.get('result', {}):
                    data = result['result']['data']
                    if data:
                        # Pretty print the first few rows
                        print("\nData:")
                        for i, row in enumerate(data[:5]):
                            print(f"Row {i+1}: {json.dumps(row, indent=2)}")
                        
                        if len(data) > 5:
                            print(f"...and {len(data) - 5} more rows")
                    else:
                        print("\nNo data returned")
                
                # Print discrepancies
                discrepancies = result.get('discrepancies', [])
                if discrepancies:
                    print(f"\nFound {len(discrepancies)} discrepancies:")
                    for i, disc in enumerate(discrepancies[:3]):
                        print(f"  {i+1}. {disc['message']}")
                    
                    if len(discrepancies) > 3:
                        print(f"  ...and {len(discrepancies) - 3} more discrepancies")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error("Please make sure Oracle DB connection details and AWS credentials are properly configured in .env file")


if __name__ == "__main__":
    main()
