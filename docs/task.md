# Performance Optimization: Async Analysis & Caching

## 1. Architectural Changes

- [x] Update Database Models
  - [x] Add `Study.analysis_status` (PENDING, RUNNING, COMPLETED, FAILED)
  - [x] Add `Study.last_analyzed_at`
  - [x] Add `Study.analysis_progress` (0-100)
  - [x] Ensure `Study` has fields for cached JSON risk/issues data
- [x] Create Background Worker
  - [x] Create `AnalysisWorker` class (threading based)
  - [x] Implement `run_analysis_async` function
  - [x] Ensure thread safety for DB operations (new session per thread)

## 2. Core Pipeline Updates

- [x] Refactor `Pipeline`
  - [x] Split `analyze_study` into synchronous setup and async execution
  - [x] Implement incremental analysis (check for new files only)
  - [x] Add status updates during analysis steps

## 3. UI Refactoring (Lazy Loading)

- [x] Dashboard Loading State
  - [x] Display "Analysis in Progress" banner if status != COMPLETED
  - [x] Add poll mechanism (st.rerun or fragment) to check status
- [x] Cached Data Display
  - [x] Update dashboard to read *only* from `Study` model fields (no re-calculation)
- [x] Issues Table Pagination
  - [x] Implement server-side pagination for `get_study_issues`
  - [x] Update UI to show 50 rows per page with Next/Prev buttons

## 4. Verification

- [x] Test Upload -> Background process -> Completion
- [x] Verify UI assumes non-blocking state
- [x] Test large study performance
