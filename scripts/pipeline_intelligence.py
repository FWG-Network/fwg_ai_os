import sys
import subprocess

# Define files that are critical to the system's core functionality.
# Changes to these files imply higher risk.
CRITICAL_FILES = {
    # Autonomous Core
    "backend/aios/autonomous_loop.py",
    "backend/aios/executor.py",
    "backend/aios/task_planner.py",
    # LLM Brain
    "backend/llm/orchestrator.py",
    "backend/llm/rag_pipeline.py",
    # Infrastructure & Deployment
    "docker-compose.yml",
    "Dockerfile",
    ".github/workflows/ci-cd-pipeline.yml"
}

def get_changed_files(before_sha, after_sha):
    """Gets a list of changed files between two commits."""
    command = f"git diff --name-only {before_sha} {after_sha}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error getting git diff: {result.stderr}", file=sys.stderr)
        return []
    return result.stdout.strip().split('\n')

def analyze_risk(changed_files):
    """
    Analyzes the changed files and assigns a risk level.
    This is the core of the 'self-learning'. Over time, this could be
    enhanced to learn from past pipeline failures.
    """
    if not changed_files or not changed_files[0]:
        return "low" # No changes or only whitespace

    num_files = len(changed_files)
    critical_changes = [f for f in changed_files if f in CRITICAL_FILES]

    if critical_changes:
        print(f"High-risk change detected in critical files: {critical_changes}", file=sys.stderr)
        return "high"
    
    if num_files > 20: # A large number of changes is inherently riskier
        return "medium"

    # Default to low risk for small, non-critical changes
    return "low"

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python pipeline_intelligence.py <before_sha> <after_sha>", file=sys.stderr)
        sys.exit(1)
        
    before = sys.argv[1]
    after = sys.argv[2]
    
    files = get_changed_files(before, after)
    risk = analyze_risk(files)
    print(risk) # This output is captured by the GitHub Action
