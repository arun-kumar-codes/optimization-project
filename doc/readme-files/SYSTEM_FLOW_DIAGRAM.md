# Test Case Optimization System - Complete Flow Diagram

## System Architecture Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INPUT PHASE                                       │
│                                                                             │
│  ┌──────────────────────┐      ┌──────────────────────┐                   │
│  │  Test Cases JSON     │      │  Steps JSON Files    │                   │
│  │  (01.json to 55.json)│      │  (01.json to 55.json)│                   │
│  │                      │      │                      │                   │
│  │  - Metadata          │      │  - Step details      │                   │
│  │  - Test case info    │      │  - Actions           │                   │
│  │  - Priority          │      │  - Elements          │                   │
│  │  - Status            │      │  - Test data         │                   │
│  └──────────────────────┘      └──────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: DATA LOADING & VALIDATION                      │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  DataLoader                                                   │         │
│  │  - Loads all test case JSON files                            │         │
│  │  - Loads all step JSON files                                  │         │
│  │  - Parses into TestCase and TestStep objects                 │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  DataValidator                                               │         │
│  │  - Validates data completeness                               │         │
│  │  - Checks for missing fields                                 │         │
│  │  - Reports errors and warnings                               │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  Data Normalization                                          │         │
│  │  - Normalizes action names                                  │         │
│  │  - Standardizes element identifiers                         │         │
│  │  - Cleans descriptions                                      │         │
│  └─────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              PHASE 2: STEP-LEVEL ANALYSIS & DUPLICATE DETECTION             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  StepUniquenessAnalyzer                                      │         │
│  │  - Identifies unique steps in each test case                │         │
│  │  - Calculates step signatures (hash-based)                  │         │
│  │  - Compares steps using fuzzy matching                      │         │
│  │  - Generates uniqueness scores                              │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  StepCoverageTracker                                         │         │
│  │  - Builds step coverage map                                 │         │
│  │  - Tracks which test cases cover which steps                │         │
│  │  - Calculates step coverage percentage                      │         │
│  │  - Identifies uncovered steps                               │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  DuplicateDetector                                           │         │
│  │  - Extracts sequences (actions, elements, flows)            │         │
│  │  - Calculates similarity using:                             │         │
│  │    • Levenshtein distance                                   │         │
│  │    • Longest Common Subsequence (LCS)                       │         │
│  │    • Step-level comparison                                 │         │
│  │  - Groups into:                                             │         │
│  │    • Exact duplicates (100% similar)                       │         │
│  │    • Near duplicates (>90% similar)                        │         │
│  │    • Highly similar (>75% similar)                          │         │
│  └─────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 3: USER FLOW ANALYSIS                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  FlowAnalyzer                                                │         │
│  │  - Identifies flow types (auth, CRUD, navigation, etc.)     │         │
│  │  - Extracts page transitions                                │         │
│  │  - Finds flow boundaries                                    │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  FlowGraph (NetworkX)                                       │         │
│  │  - Builds graph of user flows                               │         │
│  │  - Nodes = Pages/States                                     │         │
│  │  - Edges = Transitions                                      │         │
│  │  - Identifies critical paths                                │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  CoverageAnalyzer                                            │         │
│  │  - Calculates flow coverage                                │         │
│  │  - Identifies critical flows                                │         │
│  │  - Creates coverage matrix                                 │         │
│  │  - Finds coverage gaps                                      │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  FlowClassifier                                             │         │
│  │  - Classifies test cases by flow type                       │         │
│  │  - Groups by category (admin vs user)                       │         │
│  │  - Identifies primary/secondary flows                        │         │
│  └─────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              PHASE 4: AI-POWERED ANALYSIS (Optional)                        │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  ClaudeClient (Anthropic API)                               │         │
│  │  - Connects to Claude 3.5 Sonnet                           │         │
│  │  - Rate limiting                                            │         │
│  │  - Error handling                                           │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  SemanticAnalyzer                                           │         │
│  │  - Analyzes business purpose                                │         │
│  │  - Determines criticality                                   │         │
│  │  - Classifies test cases                                    │         │
│  │  - Assesses business value                                  │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  OptimizationAdvisor                                        │         │
│  │  - Provides recommendations (keep/remove/merge)             │         │
│  │  - Justifies decisions                                       │         │
│  │  - Estimates coverage impact                                │         │
│  └─────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              PHASE 5: ITERATIVE OPTIMIZATION ENGINE                          │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  Get Optimization Candidates                                │         │
│  │  - Sorted by priority:                                      │         │
│  │    1. Exact duplicates (highest priority)                  │         │
│  │    2. Near duplicates                                       │         │
│  │    3. Highly similar (lowest priority)                      │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  For Each Candidate (Iterative Loop)                       │         │
│  │                                                             │         │
│  │  ┌──────────────────────────────────────────┐             │         │
│  │  │  Try Optimization                         │             │         │
│  │  │  - Create snapshot (for rollback)        │             │         │
│  │  │  - Attempt remove or merge                │             │         │
│  │  └──────────────────────────────────────────┘             │         │
│  │              │                                             │         │
│  │              ▼                                             │         │
│  │  ┌──────────────────────────────────────────┐             │         │
│  │  │  Validate Coverage                        │             │         │
│  │  │  - Step coverage >= 95%?                 │             │         │
│  │  │  - Flow coverage >= 90%?                  │             │         │
│  │  │  - Critical flows covered?                │             │         │
│  │  │  - Unique steps preserved?                │             │         │
│  │  └──────────────────────────────────────────┘             │         │
│  │              │                                             │         │
│  │              ├─── Coverage OK ───► Apply Change            │         │
│  │              │                                             │         │
│  │              └─── Coverage Drops ───► Rollback & Skip      │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  TestCaseMerger (When Both Have Unique Steps)               │         │
│  │  - Merges steps intelligently                               │         │
│  │  - Removes duplicate steps                                  │         │
│  │  - Optimizes step order (AI-assisted)                       │         │
│  │  - Combines metadata                                        │         │
│  │  - Generates new test case ID (10000+)                      │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  Final Optimized Test Cases                                 │         │
│  │  - Kept original test cases                                │         │
│  │  - New merged test cases                                    │         │
│  │  - Removed duplicates                                       │         │
│  └─────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              PHASE 6: COMPREHENSIVE VALIDATION                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  CoverageValidator                                           │         │
│  │  - Step coverage validation (>=95%)                         │         │
│  │  - Flow coverage validation (>=90%)                         │         │
│  │  - Element coverage validation                              │         │
│  │  - Scenario coverage validation                              │         │
│  │  - Data coverage validation                                 │         │
│  │  - Generates validation report                              │         │
│  └─────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              PHASE 7: EXECUTION PLAN GENERATION                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  ExecutionPlanGenerator                                     │         │
│  │  - Analyzes dependencies                                    │         │
│  │  - Calculates priorities                                    │         │
│  │  - Groups for parallel execution                            │         │
│  │  - Estimates execution time                                 │         │
│  │  - Creates execution order:                                 │         │
│  │    • Smoke tests (highest priority)                         │         │
│  │    • High-risk tests                                        │         │
│  │    • Regression core                                        │         │
│  │    • Nice-to-have                                           │         │
│  └─────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              PHASE 8: OUTPUT GENERATION                                     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  OutputGenerator                                             │         │
│  │  - Generates test case JSON files                           │         │
│  │  - Generates step JSON files                                │         │
│  │  - Preserves ALL metadata (pageable, version, etc.)        │         │
│  │  - Maintains exact input format                             │         │
│  │  - Separates admin/user test cases                          │         │
│  │  - Generates summary reports                                │         │
│  └─────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OUTPUT PHASE                                      │
│                                                                             │
│  ┌──────────────────────┐      ┌──────────────────────┐                 │
│  │  Optimized Test Cases │      │  Optimized Steps      │                 │
│  │  (01.json, 07.json...)│      │  (01.json, 07.json...)│                 │
│  │  + Merged Test Cases  │      │  + Merged Step Files  │                 │
│  │  (14330.json, etc.)   │      │                      │                 │
│  └──────────────────────┘      └──────────────────────┘                 │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │  Summary Files                                               │         │
│  │  - optimization_summary.json                                 │         │
│  │  - execution_order.json                                      │         │
│  │  - duplicate_analysis.json                                   │         │
│  │  - admin_optimized_tests.json                               │         │
│  │  - user_optimized_tests.json                                │         │
│  │  - user_flows.json                                          │         │
│  │  - recommendations.json                                     │         │
│  └─────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Features Highlighted

### 1. **Step-Level Safety**
   - Every removal/merge is validated at step level
   - Unique steps are preserved
   - Coverage maintained at 95%+ for steps

### 2. **Iterative Optimization**
   - One change at a time
   - Rollback if coverage drops
   - Safe optimization guaranteed

### 3. **Intelligent Merging**
   - Combines similar test cases
   - Preserves all unique steps
   - Creates new test cases with new IDs

### 4. **Comprehensive Validation**
   - Multi-level coverage checks
   - Step, flow, element, scenario, data coverage
   - Detailed validation reports

### 5. **Metadata Preservation**
   - All original fields preserved
   - Same format as input
   - Ready to use in your application

## Metrics Tracked

- **Reduction**: Test cases reduced (typically 40-60%)
- **Coverage**: Flow coverage (maintained at 90%+)
- **Step Coverage**: Step coverage (maintained at 95%+)
- **Time Savings**: Execution time reduced
- **Merged Cases**: Number of merged test cases created


