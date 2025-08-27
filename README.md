# SQL Agent

A sophisticated deep agent capable of intelligently querying Oracle databases based on natural language input and identifying data discrepancies using AWS Bedrock's Claude 3 models.

## Features

- **Natural Language Processing**: Translate user queries into optimized SQL
- **Schema Intelligence**: Automatically selects appropriate schemas and tables
- **Memory Module**: Retains context across sessions for improved responses
- **Planning Tools**: Breaks down complex queries into executable steps
- **Sub-Agents**: Specialized agents handle different aspects of database interaction
- **Discrepancy Detection**: Identifies inconsistencies based on business logic

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from sql_agent import SQLAgent

# Initialize the agent (using environment variables from .env file)
agent = SQLAgent()

# Or initialize with explicit parameters
agent = SQLAgent(
    bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    bedrock_region="us-east-1"
)

# Set business rules for discrepancy detection
agent.set_business_logic({
    "rule_name": {
        "description": "Check for data discrepancies",
        "severity": "medium",
        "sql_query": "YOUR SQL QUERY TO DETECT DISCREPANCIES",
        "message": "Description of the discrepancy"
    }
})

# Ask a question in natural language
result = agent.query("Show me all customers who made purchases last month")

# Print the result
print(result)
```

## Configuration

Create a `.env` file with your Oracle database connection details and AWS Bedrock credentials:

```
# Oracle Database Configuration
ORACLE_USER=your_oracle_username
ORACLE_PASSWORD=your_oracle_password
ORACLE_DSN=your_oracle_dsn

# AWS Bedrock Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_SESSION_TOKEN=your_session_token  # For temporary credentials
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

## Development

This project uses Python 3.8+ and relies on several libraries for its functionality.

### Project Structure

- `sql_agent/`: Core agent code
  - `agent.py`: Main agent implementation
  - `memory.py`: Memory module implementation
  - `planner.py`: Planning module for query decomposition
  - `bedrock_agent.py`: Amazon Bedrock integration
  - `sub_agents/`: Specialized agents for different tasks
    - `schema_agent.py`: Selects appropriate database schema
    - `query_agent.py`: Generates and executes SQL queries
    - `discrepancy_agent.py`: Detects data inconsistencies
  - `utils/`: Utility functions
    - `db_utils.py`: Database connection utilities

## Running the Example

The project includes an example script that demonstrates the SQL Agent's capabilities:

```bash
# Make sure your .env file is configured first
python -m sql_agent.run
```

This will start an interactive session where you can enter natural language queries to interact with your Oracle database.

## License

MIT
