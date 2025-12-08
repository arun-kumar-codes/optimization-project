# Test Case Optimization System

An AI-powered system to optimize test suites by removing duplicates while maintaining high user flow coverage.

## Features

- **Duplicate Detection**: Identifies exact, near, and highly similar test cases
- **Flow Analysis**: Models user flows and analyzes coverage
- **AI-Powered Analysis**: Uses Claude API for semantic understanding
- **Smart Optimization**: Removes duplicates while maintaining >90% coverage
- **Execution Ordering**: Generates optimal execution order with priorities
- **Output Generation**: Creates optimized test files in same format as input

## Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- Virtual environment (recommended)

### 2. Setup

```bash
# Navigate to the project directory
cd test_optimizer

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Key

Create a `.env` file in the `test_optimizer` directory:

```bash
# Create .env file
cat > .env << EOF
ANTHROPIC_API_KEY=your_api_key_here
EOF
```

**Note**: The `.env` file is already in `.gitignore` and won't be committed.

### 4. Prepare Input Data

Ensure your test case data is in the following structure:

```
json-data/
├── test_cases/
│   ├── 01.json
│   ├── 02.json
│   └── ...
└── steps_in_test_cases/
    ├── 01.json
    ├── 02.json
    └── ...
```

### 5. Run Optimization

```bash
# Basic usage (uses default paths)
python main.py

# With custom paths
python main.py \
    --input-test-cases ../json-data/test_cases \
    --input-steps ../json-data/steps_in_test_cases \
    --output-dir ../json-data/output

# Skip AI analysis (faster, no API costs)
python main.py --skip-ai

# Limit AI analysis to save costs
python main.py --ai-limit 10

# Custom minimum coverage
python main.py --min-coverage 0.95
```

## Command Line Options

```
--input-test-cases PATH    Path to test cases directory (default: ../json-data/test_cases)
--input-steps PATH         Path to steps directory (default: ../json-data/steps_in_test_cases)
--output-dir PATH          Path to output directory (default: ../json-data/output)
--min-coverage FLOAT       Minimum coverage to maintain (default: 0.90)
--skip-ai                  Skip AI analysis to save API costs
--ai-limit N               Limit AI analysis to N test cases
```

## Output Files

The system generates the following files in the output directory:

### Optimized Test Files (Same Format as Input)
- `test_cases/XX.json` - Optimized test case metadata files
- `steps_in_test_cases/XX.json` - Optimized test step files

**These files can be used directly in your application!**

### Analysis Files
- `admin_optimized_tests.json` - List of admin test case IDs
- `user_optimized_tests.json` - List of user test case IDs
- `optimization_summary.json` - High-level optimization metrics
- `duplicate_analysis.json` - Detailed duplicate groups
- `execution_order.json` - Optimal execution order
- `user_flows.json` - Flow coverage analysis
- `recommendations.json` - Optimization recommendations

## Project Structure

```
test_optimizer/
├── main.py                 # Main orchestrator script
├── requirements.txt        # Python dependencies
├── .env                   # API key (create this)
├── README.md              # This file
│
├── data/                   # Phase 1: Data processing
│   ├── data_loader.py
│   ├── models.py
│   ├── normalizers.py
│   └── validator.py
│
├── analysis/              # Phase 2: Similarity analysis
│   ├── sequence_extractor.py
│   ├── similarity_analyzer.py
│   ├── duplicate_detector.py
│   └── similarity_matrix.py
│
├── flows/                 # Phase 3: Flow modeling
│   ├── flow_analyzer.py
│   ├── flow_graph.py
│   ├── coverage_analyzer.py
│   └── flow_classifier.py
│
├── ai/                    # Phase 4: AI analysis
│   ├── claude_client.py
│   ├── semantic_analyzer.py
│   ├── optimization_advisor.py
│   └── gap_analyzer.py
│
├── optimization/          # Phase 5: Optimization
│   ├── optimization_engine.py
│   ├── coverage_validator.py
│   ├── test_case_merger.py
│   └── optimization_report.py
│
├── execution/             # Phase 6: Execution ordering
│   ├── dependency_analyzer.py
│   ├── priority_calculator.py
│   ├── execution_scheduler.py
│   └── execution_plan.py
│
└── output/                # Phase 7: Output generation
    ├── output_generator.py
    ├── report_formatter.py
    └── output_validator.py
```

## How It Works

1. **Loads** all test cases from JSON files
2. **Analyzes** similarity and detects duplicates
3. **Models** user flows and calculates coverage
4. **Uses AI** to understand business value (optional)
5. **Optimizes** by removing duplicates while maintaining coverage
6. **Generates** execution order based on priorities
7. **Outputs** optimized test files in same format as input

## Example Usage

```bash
# Run full optimization
python main.py

# Output:
# PHASE 1: Loading Test Cases...
# ✓ Loaded 43 test cases
# 
# PHASE 2: Detecting Duplicates...
# ✓ Found 2 duplicate groups
# 
# PHASE 3: Analyzing User Flows...
# ✓ Identified 7 unique flows
# ✓ Coverage: 100.0%
# 
# PHASE 5: Optimizing Test Suite...
# ✓ Optimization completed
#   Original: 43 test cases
#   Optimized: 17 test cases
#   Reduction: 26 (60.5%)
#   Coverage: 100.0%
# 
# PHASE 7: Generating Output Files...
# ✓ All output files generated
```

## Cost Considerations

- **AI Analysis (Phase 4)**: Makes API calls to Claude, which incurs costs
- **Skip AI**: Use `--skip-ai` flag to skip AI analysis (still works well!)
- **Limit AI**: Use `--ai-limit N` to analyze only N test cases

## Troubleshooting

### Import Errors
If you see import errors, make sure:
1. Virtual environment is activated
2. Dependencies are installed: `pip install -r requirements.txt`
3. You're running from the `test_optimizer` directory

### API Key Issues
If AI analysis fails:
1. Check `.env` file exists and has correct API key
2. Verify API key is valid
3. Use `--skip-ai` to continue without AI

### File Not Found
If input files aren't found:
1. Check paths are correct
2. Use absolute paths if needed
3. Verify JSON files exist in specified directories

## Sharing with Others

To share this code with others:

1. **Remove `.env` file** (it's in `.gitignore`, so won't be committed)
2. **Share the code** (all code, requirements.txt, README.md)
3. **Instructions for others**:
   - Install dependencies: `pip install -r requirements.txt`
   - Create `.env` file with their API key
   - Run: `python main.py`

## Support

For issues or questions, check:
- Individual phase READMEs (README_PHASE1.md, etc.)
- Test scripts (test_phase1.py, etc.) for examples
- Code comments for detailed explanations

## License

[Add your license here]


