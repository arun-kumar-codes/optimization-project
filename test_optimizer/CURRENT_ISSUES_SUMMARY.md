# Current Issues Summary - TC 87595

## Critical Issues Found

### 1. Admin Credentials in Merged Test Case ❌
**TC 87595** (22 test cases merged) contains:
- **Step 3**: "Enter Admin in the username field" with testData: "Admin"
- **Problem**: This merged test case contains both admin and user test cases, resulting in admin credentials appearing in what should be a user flow

### 2. Duplicate Login Steps ⚠️
**TC 87595** has duplicate login sequence:
- **Steps 1-6**: Initial login sequence (navigateTo → click username → enter Admin → click password → enter admin123 → click Login)
- **Steps 7-10**: Duplicate login sequence AFTER already logged in:
  - Step 7: Click on Username
  - Step 8: Press Shift Key
  - Step 9: Enter Admin in the Username field
  - Step 10: Enter admin123 in the Password field

This matches the image you shared showing the duplicate login steps.

## Root Cause Analysis

### Why All 22 Test Cases Were Merged Together

The test cases are being merged because they're all in the same `(role, website)` group. This suggests:

1. **Role Classification Issue**: Some test cases with admin credentials (like "Admin" username) are not being classified as "admin"
2. **Grouping Issue**: The role-aware grouping is not properly separating admin and user test cases

### Why Duplicate Login Steps Appear

The duplicate login detection logic was removed from `test_case_merger.py`, so the merger is no longer excluding duplicate login steps from middle sections.

## Fixes Applied

1. ✅ **Enhanced Flow Validation**: Added detection for:
   - Duplicate login sequences (login steps after position 10)
   - Admin credentials in user flows (checks if all source test cases are "user" and detects "Admin" in testData)

2. ✅ **Post-Merge Validation**: The `MergedTestCaseValidator` now checks for:
   - Admin credentials in user flows
   - Duplicate login sequences

## Next Steps Required

### Option 1: Re-enable Case-Sensitive Admin Detection
The role classifier needs to detect "Admin" (capital A) as a strong admin indicator. Currently, it only checks lowercase "admin".

### Option 2: Re-enable Duplicate Login Detection
The merger needs to exclude duplicate login steps from middle sections. The logic was removed but should be restored.

### Option 3: Split TC 87595
Manually split TC 87595 into separate admin and user flows based on role classification.

## Current Validation Results

When running `validate_merged_test_cases.py`, it should now detect:
- ❌ Admin credentials in user flow (for TC 87595 if it's classified as user)
- ⚠️ Duplicate login sequence (steps 7-10 in TC 87595)

## Recommendation

1. **Immediate**: Run the validation script to confirm it detects the issues
2. **Short-term**: Re-enable case-sensitive "Admin" detection in role classifier
3. **Short-term**: Re-enable duplicate login step exclusion in merger
4. **Long-term**: Ensure role-aware grouping properly separates admin and user test cases



