#!/usr/bin/env bash
# PeatGuard Supervisor Agent
# Delegates work to parallel Claude Code agents, manages branches, merges results.
#
# Usage: ./scripts/supervisor.sh [--dry-run] [--skip-cloud]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

DRY_RUN=false
SKIP_CLOUD=false
for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=true ;;
    --skip-cloud) SKIP_CLOUD=true ;;
  esac
done

# --- Configuration ---
MAIN_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
WORKTREE_DIR="$REPO_ROOT/.worktrees"
LOG_DIR="$REPO_ROOT/.worktrees/logs"
MERGE_BRANCH="supervisor/merge-$(date +%Y%m%d-%H%M%S)"

# Task definitions: name|branch|prompt|touches_orchestrator
TASKS=(
  "grd-prefix|fix/grd-prefix|Fix the GRD download GCS prefix bug. In src/peatguard/ingest/download.py the gcs_prefix parameter defaults to 'raw/slc' for ALL processing levels. When downloading GRD_HD files, they should go to 'raw/grd/' not 'raw/slc/'. Also update pipeline/orchestrator.py run_download_stage() to pass the correct prefix based on processing level. Run pytest when done.|false"
  "error-handling|fix/error-handling|Fix all bare 'except Exception: pass' clauses in src/peatguard/pipeline/orchestrator.py. There are silent failures around the catalog status updates. Replace each with 'except Exception as e: logger.warning(\"...: %s\", e)' so failures are visible but non-fatal. Search for any other silent except clauses across the codebase. Run pytest when done.|true"
  "water-mask|feat/water-mask|Add water body masking to the analysis pipeline. Create a water_mask() function in src/peatguard/analysis/ that thresholds VV backscatter (sigma0 < 0.016 or about -18 dB) to identify water pixels. Apply this mask in subsidence_class.py so water pixels become NoData (-9999) instead of false 'severe subsidence'. Update pipeline/orchestrator.py run_analysis_stage() to apply the water mask when VV composite is available. Add a test in tests/test_analysis.py. Run pytest when done.|true"
  "canal-risk|feat/canal-risk-prep|Review src/peatguard/analysis/canal_detect.py, analysis/risk_score.py, and pipeline/orchestrator.py run_analysis_stage(). Ensure run_analysis_stage() correctly: (1) downloads VV composite from GCS if not available locally, (2) passes it to canal_detect, (3) feeds canal_distance into risk_score, (4) handles CRS reprojection between canal_distance and velocity grids. Fix any bugs found. Run pytest tests/test_analysis.py when done.|true"
)

# --- Helper functions ---
log() { echo "[supervisor] $(date +%H:%M:%S) $*"; }
err() { echo "[supervisor] ERROR: $*" >&2; }

cleanup() {
  log "Cleaning up worktrees..."
  for task_def in "${TASKS[@]}"; do
    IFS='|' read -r name branch _ _ <<< "$task_def"
    local wt="$WORKTREE_DIR/$name"
    if [ -d "$wt" ]; then
      git worktree remove "$wt" --force 2>/dev/null || true
    fi
  done
}

# --- Phase 1: Setup worktrees ---
phase_setup() {
  log "=== Phase 1: Setting up worktrees ==="
  mkdir -p "$WORKTREE_DIR" "$LOG_DIR"

  for task_def in "${TASKS[@]}"; do
    IFS='|' read -r name branch _ _ <<< "$task_def"

    # Delete branch if it exists from a previous run
    git branch -D "$branch" 2>/dev/null || true

    local wt="$WORKTREE_DIR/$name"
    if [ -d "$wt" ]; then
      git worktree remove "$wt" --force 2>/dev/null || true
    fi

    git worktree add -b "$branch" "$wt" "$MAIN_BRANCH"
    log "  Created worktree: $name -> $branch"
  done
}

# --- Phase 2: Dispatch agents ---
phase_dispatch() {
  log "=== Phase 2: Dispatching agents ==="
  local pids=()
  local names=()

  for task_def in "${TASKS[@]}"; do
    IFS='|' read -r name branch prompt _ <<< "$task_def"
    local wt="$WORKTREE_DIR/$name"
    local logfile="$LOG_DIR/${name}.log"

    log "  Launching agent: $name"

    if $DRY_RUN; then
      echo "[dry-run] Would run claude -p in $wt" > "$logfile"
      continue
    fi

    (
      cd "$wt"
      claude -p "$prompt" \
        --allowedTools Edit,Read,Glob,Grep,Bash \
        > "$logfile" 2>&1
    ) &
    pids+=($!)
    names+=("$name")
  done

  if $DRY_RUN; then
    log "  Dry run - skipping wait"
    return
  fi

  # Wait for all agents with status reporting
  log "  Waiting for ${#pids[@]} agents..."
  local failed=()
  for i in "${!pids[@]}"; do
    if wait "${pids[$i]}"; then
      log "  Agent '${names[$i]}' completed successfully"
    else
      err "  Agent '${names[$i]}' failed (exit code $?)"
      failed+=("${names[$i]}")
    fi
  done

  if [ ${#failed[@]} -gt 0 ]; then
    err "Failed agents: ${failed[*]}"
    err "Check logs: $LOG_DIR/"
    # Continue with merge of successful ones
  fi
}

# --- Phase 3: Cloud pipeline check ---
phase_cloud() {
  if $SKIP_CLOUD; then
    log "=== Phase 3: Cloud check skipped ==="
    return
  fi

  log "=== Phase 3: Cloud pipeline status ==="

  local logfile="$LOG_DIR/cloud-check.log"

  if $DRY_RUN; then
    echo "[dry-run] Would check Cloud Run jobs" > "$logfile"
    return
  fi

  claude -p "Check PeatGuard Cloud Run job status:
1. Run: gcloud run jobs executions list --job=peatguard-backscatter --region=asia-southeast1 --limit=3
2. If the latest execution succeeded, check GCS for VV composite: gsutil ls 'gs://*/products/vv_median*.tif' (read the bucket name from config/default.yaml storage.gcs_bucket first)
3. If backscatter succeeded and VV composite exists, report READY_FOR_ANALYSIS
4. If failed, read the logs: gcloud logging read 'resource.type=cloud_run_job AND resource.labels.job_name=peatguard-backscatter' --limit=30 --format='value(textPayload)' and diagnose the failure
5. Report a clear status summary" \
    --allowedTools Read,Bash,Glob,Grep \
    > "$logfile" 2>&1

  log "  Cloud check complete. See $logfile"
  # Print the last 5 lines as summary
  tail -5 "$logfile" | sed 's/^/  /'
}

# --- Phase 4: Merge ---
phase_merge() {
  log "=== Phase 4: Merging branches ==="

  # Create merge branch
  git checkout -b "$MERGE_BRANCH" "$MAIN_BRANCH"

  # Merge order: non-orchestrator-touching branches first, then orchestrator ones
  # This minimizes conflicts
  local merge_order=()
  local merge_order_orchestrator=()

  for task_def in "${TASKS[@]}"; do
    IFS='|' read -r name branch _ touches_orch <<< "$task_def"

    # Check if branch has commits ahead of main
    local ahead
    ahead=$(git rev-list --count "$MAIN_BRANCH".."$branch" 2>/dev/null || echo "0")
    if [ "$ahead" = "0" ]; then
      log "  Skipping $name (no changes)"
      continue
    fi

    if [ "$touches_orch" = "true" ]; then
      merge_order_orchestrator+=("$name|$branch")
    else
      merge_order+=("$name|$branch")
    fi
  done

  # Merge non-conflicting branches first
  for entry in "${merge_order[@]}" "${merge_order_orchestrator[@]}"; do
    IFS='|' read -r name branch <<< "$entry"
    log "  Merging: $branch"

    if $DRY_RUN; then
      log "  [dry-run] Would merge $branch"
      continue
    fi

    if git merge "$branch" --no-edit 2>/dev/null; then
      log "  Merged $branch cleanly"
    else
      err "  Conflict merging $branch. Launching resolver agent..."
      phase_resolve_conflict "$name" "$branch"
    fi
  done

  log "  All merges complete on branch: $MERGE_BRANCH"
}

# --- Phase 4b: Conflict resolution ---
phase_resolve_conflict() {
  local name="$1"
  local branch="$2"
  local logfile="$LOG_DIR/resolve-${name}.log"

  claude -p "There is a git merge conflict merging branch '$branch' into the current branch.
Run 'git diff' and 'git status' to see the conflicts.
The conflicts are likely in pipeline/orchestrator.py since multiple agents edited it.
Resolve ALL conflicts by keeping both sets of changes (both features should coexist).
Stage the resolved files and complete the merge commit.
Run pytest to verify nothing is broken." \
    --allowedTools Edit,Read,Glob,Grep,Bash \
    > "$logfile" 2>&1

  if [ $? -eq 0 ]; then
    log "  Conflict resolved for $branch"
  else
    err "  Auto-resolution failed for $branch. Manual intervention needed."
    err "  See: $logfile"
    err "  Current state: git status"
    git merge --abort 2>/dev/null || true
  fi
}

# --- Phase 5: Validate ---
phase_validate() {
  log "=== Phase 5: Validation ==="

  if $DRY_RUN; then
    log "  [dry-run] Would run pytest"
    return
  fi

  local logfile="$LOG_DIR/validate.log"

  claude -p "Run the full test suite for PeatGuard:
1. Run: cd $REPO_ROOT && git log --oneline -10 (show what was merged)
2. Run: pytest tests/ -v
3. If any tests fail, read the failing test and the relevant source code, fix the issue, and re-run.
4. Run: git diff --stat $MAIN_BRANCH (show summary of all changes)
5. Report: which fixes were applied, test results, and whether the merge branch is ready." \
    --allowedTools Edit,Read,Glob,Grep,Bash \
    > "$logfile" 2>&1

  log "  Validation complete. See $logfile"
  tail -10 "$logfile" | sed 's/^/  /'
}

# --- Phase 6: Summary ---
phase_summary() {
  log "=== Phase 6: Summary ==="
  echo ""
  echo "Branch: $MERGE_BRANCH"
  echo "Logs:   $LOG_DIR/"
  echo ""
  echo "Changes from $MAIN_BRANCH:"
  git diff --stat "$MAIN_BRANCH" 2>/dev/null || true
  echo ""
  echo "Next steps:"
  echo "  1. Review: git log --oneline $MAIN_BRANCH..$MERGE_BRANCH"
  echo "  2. Merge:  git checkout $MAIN_BRANCH && git merge $MERGE_BRANCH"
  echo "  3. Push:   git push origin $MAIN_BRANCH"
  echo "  4. Deploy: gcloud run jobs execute peatguard-analyze --region=asia-southeast1"
  echo ""
}

# --- Main ---
main() {
  log "PeatGuard Supervisor Agent starting"
  log "Main branch: $MAIN_BRANCH"
  log "Worktrees:   $WORKTREE_DIR"
  echo ""

  trap cleanup EXIT

  phase_setup
  phase_dispatch
  phase_cloud
  phase_merge
  phase_validate
  phase_summary

  log "Supervisor complete."
}

main "$@"
