# Flow Issues Report - TC 26568 and TC 82567

## Critical Issues Found

### TC 26568 (User Consolidated Flow - 14 test cases)

#### Issue 1: Admin Credentials in User Flow ❌
- **Step 3**: "Enter Admin in the username field" with testData: "Admin"
- **Problem**: User flows should NOT use admin credentials
- **Impact**: Test will fail or execute with wrong permissions
- **Root Cause**: One of the source test cases (11, 12, 26, 36, 42, 45, 46, 47, 48, 49, 50, 51, 54, 55) uses admin credentials but was classified as "user"

#### Issue 2: Navigation After Login ⚠️
- **Step 7**: Navigates to `/dashboard/index` after login
- **Problem**: This is actually OK (going to dashboard), but the step appears redundant
- **Impact**: Minor - might cause slight delay but won't break flow

#### Flow Structure:
```
1. navigateTo (login page) ✓
2. click (username field) ✓
3. enter ("Admin" - ❌ WRONG for user flow)
4. click (password field) ✓
5. enter ("admin123" - ❌ WRONG for user flow)
6. click (Login button) ✓
7. navigateTo (dashboard) - ⚠️ Redundant but OK
8. click (Login Button) - ⚠️ Duplicate?
9-72. User actions...
```

### TC 82567 (Admin Consolidated Flow - 9 test cases)

#### Issue 1: Duplicate Login Steps ⚠️
- **Steps 1-6**: First login sequence (navigateTo → click username → enter admin → click password → enter admin123 → click login)
- **Steps 9-11**: Duplicate login steps after already logged in
- **Problem**: Login should only happen once at the beginning
- **Impact**: Will cause execution errors or unnecessary steps

#### Issue 2: Missing Element Field (But OK) ✓
- **Steps 7, 11, 13, 15-18**: Have `element: null` but element data is in `event.label` and `event.locator`
- **Status**: This is OK - API conversion handles this correctly
- **Impact**: None - elements are preserved in event field

#### Flow Structure:
```
1. navigateTo (login page) ✓
2. click (Username) ✓
3. enter ("admin") ✓
4. click (Password) ✓
5. enter ("admin123") ✓
6. click (Login) ✓
7. click (Username) - ⚠️ After login? Redundant
8. pressKey (Shift) - ⚠️ Why?
9. enter ("Admin") - ⚠️ DUPLICATE LOGIN
10. enter ("admin123") - ⚠️ DUPLICATE LOGIN
11. click (Login) - ⚠️ DUPLICATE LOGIN
12. navigateTo - ⚠️ After login?
13-48. Admin actions...
```

## Root Causes

1. **Role Classification Issue**: Some test cases using admin credentials are classified as "user"
2. **Merger Not Deduplicating Login**: The merger is including login steps from multiple test cases instead of using only the common prefix
3. **Mixed Login Scenarios**: Some test cases have login at start, others are post-login, causing duplicate login sequences

## Required Fixes

1. **Fix Role Classification**: Ensure test cases with admin credentials are classified as "admin"
2. **Fix Duplicate Login**: Ensure login steps are only included once (from common prefix)
3. **Remove Redundant Navigation**: Remove navigation steps that appear after login
4. **Validate Flow Consistency**: Add validation to detect and prevent duplicate login sequences



