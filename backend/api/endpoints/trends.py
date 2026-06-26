# backend/api/endpoints/trends.py

from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.models.db import get_db
from backend.services.connectors.youtube import youtube_connector
from backend.services.trend_analysis_service import trend_analysis_service

router = APIRouter()

# =================================================================
# ENDPOINT 1: Trigger the data collection process
# =================================================================
@router.post(
    "/scan",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Trend Data Collection",
    description="Starts a background task to scan known curator channels for new creator mentions and persists them to the database."
)
async def trigger_trend_scan(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    This endpoint initiates the 'Investigator' part of the system.
    It runs the YouTubeConnector's suggest_from_known_channels method
    in the background to avoid blocking the API.
    """
    print("API: Received request to trigger trend scan.")
    background_tasks.add_task(
        youtube_connector.suggest_from_known_channels,
        db=db,
        theme_keyword="viral trend" # Using a default, broad keyword for scanning
    )
    return {"message": "Trend data collection process started in the background."}


# =================================================================
# ENDPOINT 2: Retrieve the latest trend analysis
# =================================================================
@router.get(
    "/briefing",
    summary="Get Latest Trend Briefing",
    description="Analyzes the collected trend data and returns a ranked list of creators with the highest mention velocity."
)
def get_trend_briefing(
    db: Session = Depends(get_db)
):
    """
    This endpoint provides the 'Analyst' part of the system.
    It uses the TrendAnalysisService to calculate real-time momentum
    based on the data collected by the scanner.
    """
    print("API: Received request for trend briefing.")
    briefing_data = trend_analysis_service.calculate_mention_velocity(db)
    
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "briefing": briefing_data
    }
