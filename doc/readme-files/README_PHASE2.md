# Phase 2: Similarity Analysis and Duplicate Detection - COMPLETED

## Overview
Phase 2 successfully implements modules for analyzing test case similarity and detecting duplicates using multiple algorithms.

## What Was Created

### 1. Sequence Extractor (`analysis/sequence_extractor.py`)
- **Purpose**: Extracts sequences and patterns from test cases
- **Key Features**:
  - Extracts action sequences (ordered list of actions)
  - Extracts element sequences (which elements are interacted with)
  - Creates flow patterns (abstracted sequences)
  - Calculates longest common subsequence (LCS)
  - Compares sequences for similarity

### 2. Similarity Analyzer (`analysis/similarity_analyzer.py`)
- **Purpose**: Calculates similarity between test cases using multiple methods
- **Methods**:
  - **Sequence Similarity**: Uses Levenshtein distance on action sequences
  - **LCS Similarity**: Uses Longest Common Subsequence algorithm
  - **Step-level Similarity**: Compares individual steps (action, element, description)
  - **Flow Pattern Similarity**: Compares abstracted flow patterns
  - **Comprehensive Similarity**: Weighted combination of all methods

### 3. Duplicate Detector (`analysis/duplicate_detector.py`)
- **Purpose**: Groups duplicate and similar test cases
- **Features**:
  - Categorizes duplicates into:
    - Exact duplicates (100% similar)
    - Near duplicates (>90% similar)
    - Highly similar (>75% similar)
  - Selects best representative from each group based on:
    - Priority (higher priority = better)
    - Pass rate (better pass rate = better)
    - Execution time (shorter = better)
    - Number of steps (more comprehensive = better)
  - Provides recommendations (which to keep, which to remove)

### 4. Similarity Matrix Generator (`analysis/similarity_matrix.py`)
- **Purpose**: Generates similarity matrices for all test cases
- **Features**:
  - Creates N×N similarity matrix
  - Finds most similar pairs
  - Generates summary statistics
  - Exports to JSON format

## Test Results

**Test Run Summary:**
- ✅ 43 test cases analyzed
- ✅ 2 duplicate groups identified:
  - 1 exact duplicate (100% similarity: Test Cases 2 and 5)
  - 1 highly similar group (77.74% similarity: Test Cases 13, 14, 6)
- ✅ Top similar pairs identified:
  - Test Case 2 vs 5: 100.00% (exact duplicate)
  - Test Case 2 vs 12: 98.49%
  - Test Case 5 vs 12: 98.49%

## How It Works

### Similarity Calculation
1. **Extract sequences** from test cases (actions, elements, flow patterns)
2. **Compare sequences** using multiple algorithms:
   - Levenshtein distance (edit distance)
   - Longest Common Subsequence (LCS)
   - Step-by-step comparison
3. **Combine results** with weighted scoring
4. **Group similar test cases** using graph algorithms

### Duplicate Detection Process
1. Calculate similarity between all test case pairs
2. Build similarity graph (test cases as nodes, similarities as edges)
3. Find connected components (groups of similar test cases)
4. For each group, select the best representative
5. Recommend which test cases to keep/remove

## Example Output

```python
{
  "exact_duplicates": [
    {
      "test_case_ids": [2, 5],
      "recommended_keep": 2,
      "recommended_remove": [5],
      "max_similarity": 1.0,
      "reason": "Priority 1, 100.0% pass rate"
    }
  ],
  "highly_similar": [
    {
      "test_case_ids": [13, 14, 6],
      "recommended_keep": 13,
      "recommended_remove": [14, 6],
      "max_similarity": 0.7774,
      "reason": "Priority 1, 95.0% pass rate"
    }
  ]
}
```

## How to Use

### Basic Usage

```python
from data.data_loader import DataLoader
from analysis.duplicate_detector import DuplicateDetector

# Load test cases
loader = DataLoader("test_cases_dir", "steps_dir")
test_cases = loader.load_all()

# Detect duplicates
detector = DuplicateDetector()
duplicates = detector.detect_duplicates(test_cases)

# Get recommendations
for group in duplicates['near_duplicates']:
    print(f"Keep: {group['recommended_keep']}")
    print(f"Remove: {group['recommended_remove']}")
```

### Running the Test Script

```bash
cd test_optimizer
source venv/bin/activate
python test_phase2.py
```

## File Structure

```
test_optimizer/
├── analysis/
│   ├── __init__.py
│   ├── sequence_extractor.py    # Extract sequences
│   ├── similarity_analyzer.py   # Calculate similarities
│   ├── duplicate_detector.py    # Detect duplicates
│   └── similarity_matrix.py     # Generate matrices
└── test_phase2.py               # Test script
```

## Next Steps

Phase 2 is complete and ready for Phase 3: User Flow Modeling.

The duplicate detection results can now be used for:
- Test suite optimization
- Coverage analysis
- Execution ordering

