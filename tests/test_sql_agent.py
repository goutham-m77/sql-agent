"""
Unit tests for SQL Agent.
"""
import os
import unittest
from unittest.mock import MagicMock, patch
import tempfile
import json

from sql_agent import SQLAgent, Memory, Plan, PlanStep


class TestMemory(unittest.TestCase):
    """Tests for the Memory module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_file = tempfile.NamedTemporaryFile(delete=False).name
        self.memory = Memory(ttl=3600, persistence_path=self.test_file)
    
    def tearDown(self):
        """Tear down test fixtures."""
        if os.path.exists(self.test_file):
            os.unlink(self.test_file)
    
    def test_add_and_get(self):
        """Test adding and retrieving items from memory."""
        # Add an item
        self.memory.add("test_category", "test_item")
        
        # Retrieve items
        items = self.memory.get("test_category")
        
        # Verify
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["content"], "test_item")
    
    def test_clear(self):
        """Test clearing memory."""
        # Add items
        self.memory.add("category1", "item1")
        self.memory.add("category2", "item2")
        
        # Clear specific category
        self.memory.clear("category1")
        
        # Verify
        self.assertEqual(len(self.memory.get("category1")), 0)
        self.assertEqual(len(self.memory.get("category2")), 1)
        
        # Clear all
        self.memory.clear()
        
        # Verify
        self.assertEqual(len(self.memory.get("category2")), 0)


class TestPlan(unittest.TestCase):
    """Tests for the Plan module."""
    
    def test_plan_to_dict(self):
        """Test converting plan to dictionary."""
        # Create a plan
        step = PlanStep(
            agent="test_agent",
            action="test_action",
            description="Test description",
            params={"param1": "value1"}
        )
        plan = Plan(query="test query", steps=[step])
        
        # Convert to dict
        plan_dict = plan.to_dict()
        
        # Verify
        self.assertEqual(plan_dict["query"], "test query")
        self.assertEqual(len(plan_dict["steps"]), 1)
        self.assertEqual(plan_dict["steps"][0]["agent"], "test_agent")
        self.assertEqual(plan_dict["steps"][0]["params"]["param1"], "value1")
    
    def test_plan_from_dict(self):
        """Test creating plan from dictionary."""
        # Create a plan dict
        plan_dict = {
            "query": "test query",
            "steps": [
                {
                    "agent": "test_agent",
                    "action": "test_action",
                    "description": "Test description",
                    "params": {"param1": "value1"}
                }
            ]
        }
        
        # Create plan from dict
        plan = Plan.from_dict(plan_dict)
        
        # Verify
        self.assertEqual(plan.query, "test query")
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].agent, "test_agent")
        self.assertEqual(plan.steps[0].params["param1"], "value1")


class TestSQLAgent(unittest.TestCase):
    """Tests for the SQL Agent."""
    
    @patch('sqlalchemy.create_engine')
    def setUp(self, mock_create_engine):
        """Set up test fixtures."""
        # Mock the engine and inspector
        self.mock_engine = MagicMock()
        mock_create_engine.return_value = self.mock_engine
        
        # Mock inspector
        mock_inspector = MagicMock()
        mock_inspector.get_schema_names.return_value = ["public"]
        self.mock_engine.connect.return_value.__enter__.return_value = MagicMock()
        
        # Create agent with mocked dependencies
        with patch('sqlalchemy.inspect', return_value=mock_inspector):
            self.agent = SQLAgent(connection_string="sqlite:///:memory:")
    
    def test_initialization(self):
        """Test agent initialization."""
        self.assertIsNotNone(self.agent.memory)
        self.assertIsNotNone(self.agent.planner)
        
        if self.agent.enable_sub_agents:
            self.assertIsNotNone(self.agent.schema_agent)
            self.assertIsNotNone(self.agent.query_agent)
            self.assertIsNotNone(self.agent.discrepancy_agent)
    
    @patch('sql_agent.agent.SQLAgent._execute_plan')
    def test_query(self, mock_execute_plan):
        """Test query method."""
        # Setup mock
        mock_execute_plan.return_value = {"result": "test_result"}
        
        # Call the method
        result = self.agent.query("test query")
        
        # Verify
        self.assertEqual(result["result"], "test_result")
        mock_execute_plan.assert_called_once()
    
    def test_set_business_logic(self):
        """Test setting business logic."""
        # Skip if sub-agents not enabled
        if not self.agent.enable_sub_agents:
            return
            
        # Set business logic
        rules = {"rule1": {"description": "Test rule"}}
        self.agent.set_business_logic(rules)
        
        # Verify
        self.assertEqual(self.agent.discrepancy_agent.business_rules, rules)


if __name__ == '__main__':
    unittest.main()
