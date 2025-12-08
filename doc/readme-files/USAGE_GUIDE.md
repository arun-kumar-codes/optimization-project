# Complete Usage Guide

## How to Run the System

### Prerequisites Check

1. **Python 3.8+** installed
2. **Virtual environment** created and activated
3. **Dependencies** installed
4. **API key** configured in `.env` file (optional, can skip AI)

### Step-by-Step Instructions

#### 1. Navigate to Project Directory
```bash
cd /path/to/optimization/test_optimizer
```

#### 2. Activate Virtual Environment
```bash
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows
```

#### 3. Verify Setup
```bash
# Check Python version
python --version  # Should be 3.8+

# Check dependencies
pip list | grep anthropic  # Should show anthropic package
```

#### 4. Configure API Key (Optional)
```bash
# Create .env file
echo "ANTHROPIC_API_KEY=your_key_here" > .env
```

#### 5. Run Optimization
```bash
python main.py
```

## Command Examples

### Basic Run (Full Optimization)
```bash
python main.py
```
- Uses default paths
- Runs all phases including AI
- Generates all output files

### Skip AI Analysis
```bash
python main.py --skip-ai
```
- Faster execution
- No API costs
- Still optimizes based on algorithmic analysis

### Custom Paths
```bash
python main.py \
    --input-test-cases /path/to/test_cases \
    --input-steps /path/to/steps \
    --output-dir /path/to/output
```

### Limit AI Analysis
```bash
python main.py --ai-limit 5
```
- Analyzes only 5 test cases with AI
- Reduces API costs
- Good for testing

### Custom Coverage Threshold
```bash
python main.py --min-coverage 0.95
```
- Maintains 95% coverage instead of default 90%

## Understanding the Output

### Main Output Files (Use These!)

**`test_cases/XX.json`**
- Optimized test case metadata
- Same format as your input files
- **Use directly in your application**

**`steps_in_test_cases/XX.json`**
- Optimized test steps
- Same format as your input files
- **Use directly in your application**

### Reference Files

**`admin_optimized_tests.json`**
```json
{
  "admin_test_case_ids": [37, 40, 43, ...],
  "count": 6
}
```
- List of admin test case IDs to run

**`user_optimized_tests.json`**
```json
{
  "user_test_case_ids": [1, 2, 5, ...],
  "count": 11
}
```
- List of user test case IDs to run

**`execution_order.json`**
- Optimal order to run tests
- Includes priorities, estimated times
- Use for test execution scheduling

**`optimization_summary.json`**
- High-level metrics
- Before/after comparison
- Time savings

## Sharing with Others

### What to Share

1. **All code files** (everything in `test_optimizer/`)
2. **`requirements.txt`** (dependencies)
3. **`README.md`** and **`QUICK_START.md`** (documentation)
4. **`.gitignore`** (to exclude `.env`)

### What NOT to Share

- `.env` file (contains API key)
- `venv/` directory (virtual environment)
- Output files (generated, not needed)

### Instructions for Others

Tell them to:
1. Clone/copy the code
2. Create virtual environment: `python3 -m venv venv`
3. Activate: `source venv/bin/activate`
4. Install: `pip install -r requirements.txt`
5. Create `.env` with their API key
6. Run: `python main.py`

## Troubleshooting

### "Module not found" errors
```bash
# Solution: Activate venv and install dependencies
source venv/bin/activate
pip install -r requirements.txt
```

### "ANTHROPIC_API_KEY not found"
```bash
# Solution: Create .env file
echo "ANTHROPIC_API_KEY=your_key" > .env
# OR use --skip-ai flag
python main.py --skip-ai
```

### "File not found" errors
```bash
# Solution: Check paths, use absolute paths
python main.py \
    --input-test-cases /absolute/path/to/test_cases \
    --input-steps /absolute/path/to/steps
```

### Import errors
```bash
# Solution: Make sure you're in test_optimizer directory
cd test_optimizer
python main.py
```

## Expected Runtime

- **Without AI**: ~30 seconds to 2 minutes (depending on test case count)
- **With AI**: ~5-10 minutes (depends on API response time and test case count)
- **With AI limit**: ~2-5 minutes (faster, limited analysis)

## Output File Sizes

Typical output for 43 test cases:
- `test_cases/`: ~17 files (optimized)
- `steps_in_test_cases/`: ~17 files (optimized)
- Summary JSON files: ~50-100 KB total

## Next Steps After Optimization

1. **Review** `optimization_summary.json` to understand what was optimized
2. **Check** `admin_optimized_tests.json` and `user_optimized_tests.json`
3. **Use** optimized files from `test_cases/` and `steps_in_test_cases/` in your application
4. **Follow** `execution_order.json` for optimal test execution

## Support

- Check `README.md` for detailed documentation
- Check phase-specific READMEs (README_PHASE1.md, etc.)
- Review test scripts (test_phase1.py, etc.) for examples


