#!/usr/bin/env bash
# =============================================================================
# PeatGuard Automated Scheduling Setup
# =============================================================================
#
# Sets up Cloud Scheduler + Cloud Workflows for monthly pipeline reprocessing.
#
# What this creates:
#   1. Cloud Workflow "peatguard-monthly" -- orchestrates the 5 pipeline stages
#   2. Cloud Scheduler job "peatguard-monthly-trigger" -- fires on the 1st of
#      each month at 06:00 WIB (Asia/Jakarta)
#
# Pipeline execution order (managed by the workflow):
#   ingest -> (insar + backscatter in parallel) -> timeseries -> analyze
#
# Prerequisites:
#   - gcloud CLI authenticated with project owner/editor
#   - APIs enabled: workflows.googleapis.com, cloudscheduler.googleapis.com,
#     run.googleapis.com
#   - Service account peatguard-sa@ exists with Cloud Run Invoker role
#   - All 5 Cloud Run Jobs already created (see cloudrun-job.yaml)
#
# Usage:
#   cd peatguard/peatguard
#   bash cloud/scheduler-setup.sh           # deploy workflow + scheduler
#   bash cloud/scheduler-setup.sh --pause   # pause the scheduler
#   bash cloud/scheduler-setup.sh --resume  # resume the scheduler
#   bash cloud/scheduler-setup.sh --status  # show current status
#   bash cloud/scheduler-setup.sh --delete  # remove scheduler + workflow
#   bash cloud/scheduler-setup.sh --run-now # trigger an immediate execution
#
# =============================================================================

set -euo pipefail

# -- Configuration --
PROJECT="peatguard"
REGION="asia-southeast1"
SERVICE_ACCOUNT="peatguard-sa@${PROJECT}.iam.gserviceaccount.com"
WORKFLOW_NAME="peatguard-monthly"
SCHEDULER_NAME="peatguard-monthly-trigger"
WORKFLOW_SOURCE="cloud/workflow.yaml"

# -- Colors for terminal output (disabled if not a tty) --
if [ -t 1 ]; then
    BOLD='\033[1m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    RED='\033[0;31m'
    RESET='\033[0m'
else
    BOLD='' GREEN='' YELLOW='' RED='' RESET=''
fi

log()  { echo -e "${GREEN}[setup]${RESET} $*"; }
warn() { echo -e "${YELLOW}[setup]${RESET} $*"; }
err()  { echo -e "${RED}[setup]${RESET} ERROR: $*" >&2; }

# -- Subcommand: status --
cmd_status() {
    log "Workflow status:"
    gcloud workflows describe "${WORKFLOW_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT}" \
        --format="table(name,state,updateTime)" 2>/dev/null \
        || warn "  Workflow '${WORKFLOW_NAME}' not found."
    echo ""

    log "Scheduler status:"
    gcloud scheduler jobs describe "${SCHEDULER_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT}" \
        --format="table(name,state,schedule,timeZone,lastAttemptTime,nextRunTime)" 2>/dev/null \
        || warn "  Scheduler job '${SCHEDULER_NAME}' not found."
    echo ""

    log "Recent workflow executions (last 5):"
    gcloud workflows executions list "${WORKFLOW_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT}" \
        --limit=5 \
        --format="table(name.basename(),state,startTime,endTime)" 2>/dev/null \
        || warn "  No executions found."
}

# -- Subcommand: pause --
cmd_pause() {
    log "Pausing scheduler job '${SCHEDULER_NAME}'..."
    gcloud scheduler jobs pause "${SCHEDULER_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT}"
    log "Scheduler paused. Pipeline will not run automatically until resumed."
}

# -- Subcommand: resume --
cmd_resume() {
    log "Resuming scheduler job '${SCHEDULER_NAME}'..."
    gcloud scheduler jobs resume "${SCHEDULER_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT}"
    log "Scheduler resumed. Next run shown with --status."
}

# -- Subcommand: run-now --
cmd_run_now() {
    log "Triggering immediate workflow execution..."
    gcloud workflows run "${WORKFLOW_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT}"
    log "Workflow triggered. Monitor with: gcloud workflows executions list ${WORKFLOW_NAME} --location=${REGION} --project=${PROJECT}"
}

# -- Subcommand: delete --
cmd_delete() {
    warn "This will delete the scheduler job and workflow. Ctrl+C to cancel."
    read -r -p "Continue? [y/N] " response
    if [[ ! "$response" =~ ^[yY]$ ]]; then
        log "Aborted."
        exit 0
    fi

    log "Deleting scheduler job '${SCHEDULER_NAME}'..."
    gcloud scheduler jobs delete "${SCHEDULER_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT}" \
        --quiet 2>/dev/null || warn "  Scheduler job not found (already deleted?)."

    log "Deleting workflow '${WORKFLOW_NAME}'..."
    gcloud workflows delete "${WORKFLOW_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT}" \
        --quiet 2>/dev/null || warn "  Workflow not found (already deleted?)."

    log "Cleanup complete."
}

# -- Subcommand: deploy (default) --
cmd_deploy() {
    log "PeatGuard Automated Scheduling Setup"
    log "Project:         ${PROJECT}"
    log "Region:          ${REGION}"
    log "Service Account: ${SERVICE_ACCOUNT}"
    echo ""

    # Step 1: Enable required APIs
    log "Step 1/5: Enabling required APIs..."
    gcloud services enable \
        workflows.googleapis.com \
        cloudscheduler.googleapis.com \
        run.googleapis.com \
        --project="${PROJECT}" \
        --quiet
    log "  APIs enabled."

    # Step 2: Grant service account permissions for Workflows
    log "Step 2/5: Granting IAM roles to service account..."
    for role in "roles/workflows.invoker" "roles/run.invoker" "roles/logging.logWriter"; do
        gcloud projects add-iam-policy-binding "${PROJECT}" \
            --member="serviceAccount:${SERVICE_ACCOUNT}" \
            --role="${role}" \
            --quiet \
            --condition=None 2>/dev/null || true
    done
    log "  IAM roles granted."

    # Step 3: Deploy the Cloud Workflow
    log "Step 3/5: Deploying Cloud Workflow '${WORKFLOW_NAME}'..."
    if ! [ -f "${WORKFLOW_SOURCE}" ]; then
        err "Workflow source not found: ${WORKFLOW_SOURCE}"
        err "Run this script from peatguard/peatguard/ directory."
        exit 1
    fi

    gcloud workflows deploy "${WORKFLOW_NAME}" \
        --source="${WORKFLOW_SOURCE}" \
        --location="${REGION}" \
        --service-account="${SERVICE_ACCOUNT}" \
        --project="${PROJECT}" \
        --quiet
    log "  Workflow deployed."

    # Step 4: Create or update Cloud Scheduler job
    log "Step 4/5: Creating Cloud Scheduler job '${SCHEDULER_NAME}'..."
    # Delete existing scheduler job if it exists (update is not always reliable)
    gcloud scheduler jobs delete "${SCHEDULER_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT}" \
        --quiet 2>/dev/null || true

    gcloud scheduler jobs create http "${SCHEDULER_NAME}" \
        --schedule="0 6 1 * *" \
        --uri="https://workflowexecutions.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/workflows/${WORKFLOW_NAME}/executions" \
        --http-method=POST \
        --message-body='{}' \
        --oauth-service-account-email="${SERVICE_ACCOUNT}" \
        --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform" \
        --location="${REGION}" \
        --project="${PROJECT}" \
        --time-zone="Asia/Jakarta" \
        --description="Trigger PeatGuard monthly pipeline on the 1st of each month at 06:00 WIB" \
        --attempt-deadline="30s" \
        --quiet
    log "  Scheduler job created."

    # Step 5: Verify
    log "Step 5/5: Verifying deployment..."
    echo ""
    cmd_status

    echo ""
    log "${BOLD}Setup complete.${RESET}"
    echo ""
    echo "The pipeline will run automatically on the 1st of each month at 06:00 WIB."
    echo ""
    echo "Useful commands:"
    echo "  Trigger now:   bash cloud/scheduler-setup.sh --run-now"
    echo "  Check status:  bash cloud/scheduler-setup.sh --status"
    echo "  Pause:         bash cloud/scheduler-setup.sh --pause"
    echo "  Resume:        bash cloud/scheduler-setup.sh --resume"
    echo "  Delete:        bash cloud/scheduler-setup.sh --delete"
    echo ""
    echo "Monitor executions:"
    echo "  gcloud workflows executions list ${WORKFLOW_NAME} --location=${REGION} --project=${PROJECT}"
    echo "  gcloud logging read 'resource.type=cloud_run_job AND resource.labels.job_name=~\"peatguard\"' --limit=50 --project=${PROJECT}"
}

# -- Main --
case "${1:-}" in
    --status)  cmd_status ;;
    --pause)   cmd_pause ;;
    --resume)  cmd_resume ;;
    --run-now) cmd_run_now ;;
    --delete)  cmd_delete ;;
    --help|-h)
        echo "Usage: $0 [--status|--pause|--resume|--run-now|--delete|--help]"
        echo "  (no args)   Deploy workflow + scheduler"
        echo "  --status    Show current deployment status"
        echo "  --pause     Pause the monthly scheduler"
        echo "  --resume    Resume the monthly scheduler"
        echo "  --run-now   Trigger an immediate pipeline run"
        echo "  --delete    Remove scheduler and workflow"
        ;;
    "")        cmd_deploy ;;
    *)
        err "Unknown option: $1"
        echo "Run '$0 --help' for usage."
        exit 1
        ;;
esac
