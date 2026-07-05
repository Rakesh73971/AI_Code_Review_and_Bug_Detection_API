import logging
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.ai.chains.review_chain import run_review_chain
from app.db.config import settings
from app.db.database import get_db
from app.models.code_review import CodeReview, Language, ReviewSource
from app.models.user import User

# Configure logger
logger = logging.getLogger("github_webhook")

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
)

EXTENSION_MAP = {
    ".py": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".ts": Language.JAVASCRIPT,
    ".sql": Language.SQL,
    ".java": Language.JAVA,
}

def get_language_from_filename(filename: str) -> Optional[Language]:
    for ext, lang in EXTENSION_MAP.items():
        if filename.endswith(ext):
            return lang
    return None

@router.post("/github", status_code=status.HTTP_200_OK)
async def github_webhook_handler(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    db: Session = Depends(get_db),
):
    """
    FastAPI handler for incoming GitHub webhooks.
    Listens for 'pull_request' events (specifically 'opened' and 'synchronize').
    """
    logger.info(f"Received GitHub webhook event: {x_github_event}")

    if x_github_event != "pull_request":
        return {"message": f"Ignored event type: {x_github_event}"}

    payload = await request.json()
    action = payload.get("action")
    
    # We only review on PR opened or updated (synchronize)
    if action not in ["opened", "synchronize"]:
        return {"message": f"Ignored pull request action: {action}"}

    pull_request = payload.get("pull_request", {})
    pr_number = payload.get("number")
    repository = payload.get("repository", {})
    repo_full_name = repository.get("full_name")  # e.g. "owner/repo"
    commit_sha = pull_request.get("head", {}).get("sha")
    pr_html_url = pull_request.get("html_url")
    pr_author = pull_request.get("user", {}).get("login")

    if not repo_full_name or not pr_number or not commit_sha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required pull request payload fields."
        )

    # 1. Determine user to associate with the review
    # Look for a user with the matching GitHub username
    reviewer_user = db.query(User).filter(User.github_name == pr_author).first()
    if not reviewer_user:
        # Fallback to first user in system (or admin)
        reviewer_user = db.query(User).order_by(User.id.asc()).first()
        if not reviewer_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No registered users found in the system to assign the review."
            )

    # 2. Get GITHUB_TOKEN
    token = settings.github_token
    headers = {}
    if token and "your_github" not in token:
        headers["Authorization"] = f"token {token}"
    
    # Fetch pull request files
    github_api_base = f"https://api.github.com/repos/{repo_full_name}"
    files_url = f"{github_api_base}/pulls/{pr_number}/files"
    
    reviews_completed = []

    try:
        # Fetch list of modified files in the PR
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(files_url, headers=headers)
            if res.status_code != 200:
                logger.error(f"Failed to fetch files from GitHub API: {res.text}")
                # If token is invalid or missing, we continue using local test payload
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to query files from GitHub: {res.text}"
                )
            
            pr_files = res.json()
            
            comments_payload = []
            overall_quality_sum = 0
            reviewed_files_count = 0

            for pr_file in pr_files:
                filename = pr_file.get("filename")
                status_file = pr_file.get("status")
                
                # Skip deleted files
                if status_file == "removed":
                    continue
                    
                language = get_language_from_filename(filename)
                if not language:
                    continue  # Skip unsupported files

                # Fetch raw content of the file at this commit sha
                raw_url = pr_file.get("raw_url")
                raw_res = await client.get(raw_url, headers=headers)
                if raw_res.status_code != 200:
                    logger.warning(f"Could not download file content for {filename}: {raw_res.text}")
                    continue
                
                file_content = raw_res.text
                
                # Run the AI review chain on the code
                # Language enum value is string e.g. "python", "javascript"
                review_output, doc_sources = run_review_chain(
                    language=language.value,
                    code=file_content,
                    use_rag=True
                )
                
                reviewed_files_count += 1
                overall_quality_sum += review_output.quality_score
                
                # Save the review in database
                db_review = CodeReview(
                    user_id=reviewer_user.id,
                    language=language,
                    original_code=file_content,
                    bugs_found=[bug.model_dump() for bug in review_output.bugs_found],
                    severity_summary=review_output.severity_summary.model_dump(),
                    suggestions=review_output.suggestions,
                    quality_score=review_output.quality_score,
                    doc_sources_used=doc_sources,
                    source=ReviewSource.GITHUB_PR,
                    github_pr_url=pr_html_url
                )
                db.add(db_review)
                db.commit()
                db.refresh(db_review)
                
                reviews_completed.append({
                    "file": filename,
                    "review_id": db_review.id,
                    "quality_score": review_output.quality_score,
                    "bugs_found_count": len(review_output.bugs_found)
                })

                # Prepare inline review comments for bugs
                for bug in review_output.bugs_found:
                    # Line must be non-zero
                    bug_line = bug.line if bug.line else 1
                    comments_payload.append({
                        "path": filename,
                        "line": bug_line,
                        "side": "RIGHT",
                        "body": (
                            f"### 🤖 AI Code Review Findings\n"
                            f"**Severity:** `{bug.severity}`\n"
                            f"**Description:** {bug.description}\n"
                            f"**Suggested Fix:**\n```python\n{bug.suggested_fix}\n```" if bug.suggested_fix else ""
                        )
                    })

            # 3. Post findings back to GitHub PR
            if reviewed_files_count > 0:
                avg_score = round(overall_quality_sum / reviewed_files_count)
                
                # We post a Pull Request Review
                review_post_url = f"{github_api_base}/pulls/{pr_number}/reviews"
                
                summary_body = (
                    f"## 🤖 AI Code Review Autopilot Summary\n"
                    f"**Overall Quality Score:** `{avg_score}/100`\n"
                    f"Reviewed `{reviewed_files_count}` modified file(s). "
                    f"Check individual file comments below for detailed bug findings."
                )
                
                review_payload = {
                    "body": summary_body,
                    "event": "COMMENT",
                    "comments": comments_payload
                }
                
                # Only post review if token is available
                if token and "your_github" not in token:
                    post_res = await client.post(review_post_url, headers=headers, json=review_payload)
                    if post_res.status_code not in [200, 201]:
                        logger.warning(f"Failed to post PR review comments to GitHub: {post_res.text}")
                else:
                    logger.info("Skipped posting review to GitHub (no token configured).")
                    
    except Exception as exc:
        logger.error(f"Error executing GitHub webhook review: {exc}")
        # Return success with errors logged so webhook doesn't retry indefinitely
        return {
            "status": "error",
            "detail": str(exc),
            "reviews_completed": reviews_completed
        }

    return {
        "status": "success",
        "reviews_completed": reviews_completed
    }
