"""
Oracle database utility functions for the SQL Agent.
"""
import os
from typing import Dict, Any, Optional, Tuple
import logging
import oracledb

# Configure logging
logger = logging.getLogger(__name__)


def get_oracle_connection_params(
    username: Optional[str] = None,
    password: Optional[str] = None,
    dsn: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get connection parameters for Oracle DB.
    
    If any parameter is not provided, it will be loaded from environment variables.
    
    Args:
        username: Database username
        password: Database password
        dsn: Oracle DSN (TNS entry name or connection string)
        
    Returns:
        Dictionary with connection parameters
    """
    # Load from environment if not provided
    username = username or os.getenv("ORACLE_USER", "system")
    password = password or os.getenv("ORACLE_PASSWORD", "")
    dsn = dsn or os.getenv("ORACLE_DSN", "")
    
    # Create connection parameters
    connection_params = {
        "user": username,
        "password": password,
        "dsn": dsn
    }
    
    return connection_params


def create_oracle_connection(connection_params: Dict[str, Any] = None) -> oracledb.Connection:
    """
    Create an Oracle DB connection.
    
    Args:
        connection_params: Connection parameters. If None, will be loaded from environment.
        
    Returns:
        Oracle DB connection
    """
    if connection_params is None:
        connection_params = get_oracle_connection_params()
    
    try:
        # Simple direct connection using username, password, and DSN
        connection = oracledb.connect(
            user=connection_params.get("user"),
            password=connection_params.get("password"),
            dsn=connection_params.get("dsn")
        )
        
        logger.info(f"Connected to Oracle database: {connection.version}")
        return connection
        
    except Exception as e:
        logger.error(f"Oracle connection error: {e}")
        raise


def format_oracle_results(cursor: oracledb.Cursor, max_rows: int = 100) -> Dict[str, Any]:
    """
    Format Oracle query results for consistent output.
    
    Args:
        cursor: Oracle cursor with executed query
        max_rows: Maximum number of rows to include
        
    Returns:
        Formatted results as a dictionary
    """
    # Get column names from cursor description
    columns = [col[0] for col in cursor.description] if cursor.description else []
    
    # Fetch the rows
    rows = cursor.fetchmany(max_rows) if max_rows > 0 else cursor.fetchall()
    
    # Convert to list of dictionaries
    data = []
    for row in rows:
        data.append(dict(zip(columns, row)))
    
    return {
        "columns": columns,
        "data": data,
        "row_count": len(data),
        "truncated": len(data) >= max_rows,
        "rowcount": cursor.rowcount
    }
