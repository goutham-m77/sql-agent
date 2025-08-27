# Schema Optimization Plan for SQL Agent

## Problem Statement

The current implementation of the SQL Agent loads the entire database schema at initialization, which becomes problematic when dealing with very large schemas like our Medicaid rebate system (approximately 50,000+ tokens). This results in:

- High token usage costs when calling Bedrock/Claude APIs
- Slower response times
- Context window limitations
- Reduced query quality when schema is truncated

## Hybrid Solution Strategy

We will implement a multi-faceted approach to optimizing schema handling for URA mismatch analysis:

### 1. Schema Tiering

We'll organize the schema into three tiers based on frequency of use:

**Tier 1 (Always Load)**
- `MN_MCD_CLAIM_LINE` (Core table for URA comparison)
- `MN_MCD_CLAIM` (Basic claim information)
- `MN_MCD_PRICELIST_PUBLISHED` (URA reference data)

**Tier 2 (Load When Context Suggests Relevance)**
- `MN_MCD_PROGRAM` and `MN_MCD_PROGRAM_LI` (For formula verification)
- `MN_MCD_VALIDATION_MSG` (For existing validation information)
- `MN_MCD_PAYMENT` and related payment tables

**Tier 3 (Load Only When Specifically Referenced)**
- All other tables (comments, tolerances, etc.)

### 2. Query Intent Analysis

Before generating SQL, we'll perform a lightweight LLM call to determine which tables are needed:

1. Use a simplified prompt that only includes table names and high-level descriptions
2. Ask the LLM to identify which tables are needed for the specific query
3. Load detailed schema information only for those tables
4. Use the detailed schema for the main SQL generation

### 3. Schema Caching Implementation

Implement a persistent cache to avoid redundant metadata queries:

1. Store table metadata in JSON files in a cache directory
2. Include timestamp for staleness detection
3. Implement LRU (Least Recently Used) eviction policy
4. Implement background refresh for frequently used tables

### 4. Domain-Specific Patterns for URA Analysis

Create specialized handlers for common URA mismatch queries:

1. **Basic URA Mismatch Detection** - Compare SYS_CALC_URA vs INV_URA
2. **Formula Validation** - Analyze pricing components and CPI adjustments
3. **Timing Analysis** - Look for restatements and updates
4. **URA Cap Verification** - Analyze 100% AMP cap application

### 5. Progressive Relationship Discovery

Instead of loading all table relationships upfront:

1. Start with core claim-to-claimline relationship
2. Add program and pricing relationships only when needed
3. Build relationship map incrementally based on query context

## Implementation Plan

### Phase 1: Core Schema Agent Modifications (Week 1)

1. Refactor `SchemaAgent` class to support tiered schema loading
   - Add `initialize_core_schema()` method
   - Add `load_tables_detail()` method
   - Create schema caching infrastructure

2. Implement query intent analyzer
   - Create lightweight LLM prompt template
   - Add table selection logic

3. Update memory module to track schema usage patterns

### Phase 2: URA-Specific Optimizations (Week 2)

1. Create specialized business rules for URA analysis
   - Add rules for different mismatch types
   - Create pattern recognition for common URA queries

2. Implement schema relationship progressive discovery
   - Start with claim-line relationships
   - Add payment relationships when needed
   - Link to program information for formula validation

3. Add URA-specific query templates

### Phase 3: Caching and Persistence (Week 3)

1. Implement file-based schema cache
   - JSON storage of schema metadata
   - Versioning for schema changes

2. Add access tracking for LRU implementation
   - Track table usage frequency
   - Implement eviction policies

3. Create background refresh mechanism for frequently used tables

### Phase 4: Testing and Optimization (Week 4)

1. Benchmark token usage before and after implementation
2. Test with typical URA mismatch queries
3. Optimize based on real-world usage patterns
4. Document best practices for users

## Cost Benefit Analysis

### Current Approach
- Full schema: ~50,000 tokens per query
- Cost per query: ~$0.21 ($0.18 input + $0.03 output)

### Hybrid Approach (Estimated)
- Average token usage: ~5,000 tokens per query
- Cost per query: ~$0.062
- **Savings per query: ~$0.15 (70% reduction)**

### Annual Savings (Assuming 1,000 queries/month)
- Monthly savings: ~$150
- Annual savings: ~$1,800

## Next Immediate Steps

1. Create a branch for schema optimization work
2. Refactor `SchemaAgent` class to add tiered loading capability
3. Implement basic query intent analyzer
4. Add URA-specific business rules for mismatch detection
5. Set up basic schema caching framework

## Technical Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| LLM fails to correctly identify needed tables | Fall back to loading primary tables plus recently used tables |
| Increased latency from two LLM calls | Cache query intent results for similar queries |
| Cache staleness causing outdated schema info | Implement periodic validation of schema metadata |
| Missing relationship information | Provide mechanism to force full schema load when needed |

## Conclusion

By implementing this hybrid approach to schema management, we can significantly reduce token usage and costs while maintaining or improving query quality. The implementation will be done in phases, starting with core modifications to the SchemaAgent class and progressively adding more sophisticated features.
