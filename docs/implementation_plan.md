# Implementation Plan - Performance Optimization

# Goal

Eliminate UI blocking during study analysis by moving heavy computation to background threads and serving pre-computed, cached results to the dashboard.

## User Review Required
>
> [!IMPORTANT]
> This refactor changes the `Study` model schema. The database will need to be reset (deleted) or migrated. Since we are using SQLite for a scratchpad, I will likely need to recreate the DB.

## Proposed Changes

### Database Layer

#### [MODIFY] [models.py](file:///c:/Users/sagar/.gemini/antigravity/scratch/New folder/database/models.py)

- Update `Study` model:
  - Add `analysis_status` (Enum: PENDING, RUNNING, COMPLETED, FAILED)
  - Add `analysis_progress` (Integer 0-100)
  - Add `cached_analytics` (JSON/Text - store the full `analytics_json`)
  - Add `cached_risk_score` (Float)
  - Add `last_analyzed_at` (DateTime)

#### [MODIFY] [storage.py](file:///c:/Users/sagar/.gemini/antigravity/scratch/New folder/database/storage.py)

- Update `update_study_analytics` to write to new cached fields.
- Add `update_study_status(study_id, status, progress)`
- Add `get_study_status(study_id)`

### Application Layer (Async Worker)

#### [NEW] [core/worker.py](file:///c:/Users/sagar/.gemini/antigravity/scratch/New folder/core/worker.py)

- create `AnalysisWorker` class that inherits from `threading.Thread`.
- Accepts `study_id` and `file_paths`.
- Runs the pipeline `analyze_study` logic.
- Updates DB status:
    1. Set `RUNNING`
    2. Perform Extraction & Detection
    3. Update `progress`
    4. Perform Aggregation
    5. Save results to `cached_analytics`
    6. Set `COMPLETED`
- Handles exceptions by setting `FAILED`.

### Pipeline Layer

#### [MODIFY] [core/pipeline.py](file:///c:/Users/sagar/.gemini/antigravity/scratch/New folder/core/pipeline.py)

- Refactor `analyze_study` to NOT return data directly to UI, but to save to DB.
- Optimize for standard "Re-analyze" vs "Incremental" (future proofing).

### UI Layer

#### [MODIFY] [app.py](file:///c:/Users/sagar/.gemini/antigravity/scratch/New folder/app.py)

- **Upload Flow**:
  - Instead of calling `analyze_study` directly and waiting...
  - Call `worker.start_analysis_async(study_id)`
  - Show "File Uploaded. Analysis queued."
- **Dashboard Load**:
  - Check `study.analysis_status`.
  - If `RUNNING/PENDING`: Show Progress Bar + "Analyzing...". Auto-refresh (using `st.empty` or manual rerun button).
  - If `COMPLETED`: Load data structure from `study.cached_analytics`.
- **Issues Table**:
  - Implement simple pagination (slice the list from cache).

## Verification Plan

### Automated Tests

- None planned for scratchpad.

### Manual Verification

1. **Upload Test**: Upload a large CSV. Verify UI returns immediately.
2. **Status Test**: Verify "Analysis in Progress" appears in dashboard.
3. **Completion Test**: Verify dashboard updates automatically (or on refresh) when analysis is done.
4. **Performance**: Confirm page loads instantly on refresh (reading from cache).
