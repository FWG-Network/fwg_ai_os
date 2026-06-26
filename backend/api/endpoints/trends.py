# backend/api/endpoints/trends.py

from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session
from datetime import datetime

# Import the necessary components
from backend.models.db import get_db
from backend.services.connectors.youtube import youtube_connector
from backend.services.trend_analysis_service import trend_analysis_service

# Create a new router for our trend-related endpoints
router = APIRouter()


# =================================================================
# ENDPOINT 1: Trigger the data collection process
# This tells "The Investigator" to start its work.
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
    in the background to avoid blocking the API during the scan.
    """
    print("API: Received request to trigger trend scan. Starting in background...")
    
    # Use BackgroundTasks to run the long-running I/O operation
    # without making the user wait.
    background_tasks.add_task(
        youtube_connector.suggest_from_known_channels,
        db=db,
        theme_keyword="viral trend" # Using a default, broad keyword for scanning
    )
    
    return {"message": "Trend data collection process has been accepted and started in the background."}


# =================================================================
# ENDPOINT 2: Retrieve the latest trend analysis
# This asks "The Strategist" for its latest intelligence report.
# =================================================================
@router.get(
    "/briefing",
    summary="Get Latest Trend Briefing",
    description="Analyzes all collected trend data and returns a ranked list of creators with the highest mention velocity and their current lifecycle stage."
)
def get_trend_briefing(
    db: Session = Depends(get_db)
):
    """
    This endpoint provides the 'Strategist' part of the system.
    It uses the TrendAnalysisService to calculate real-time momentum
    based on the historical data collected by the scanner.
    """
    print("API: Received request for trend briefing.")
    
    # Call the upgraded service to get the analysis
    briefing_data = trend_analysis_service.get_trend_briefing(db)
    
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "briefing": briefing_data
    }
