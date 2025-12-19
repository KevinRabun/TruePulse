"""
API v1 router aggregating all endpoints.
"""

from fastapi import APIRouter

from api.v1.ads import router as ads_router
from api.v1.auth import router as auth_router
from api.v1.community_achievements import router as community_achievements_router
from api.v1.gamification import router as gamification_router
from api.v1.locations import router as locations_router
from api.v1.polls import router as polls_router
from api.v1.secure_votes import router as secure_votes_router
from api.v1.stats import router as stats_router
from api.v1.users import router as users_router
from api.v1.votes import router as votes_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(users_router, prefix="/users", tags=["Users"])
router.include_router(polls_router, prefix="/polls", tags=["Polls"])
router.include_router(votes_router, prefix="/votes", tags=["Votes"])
router.include_router(
    secure_votes_router,
    prefix="/secure-votes",
    tags=["Secure Voting (Fraud Prevention)"],
)
router.include_router(gamification_router, prefix="/gamification", tags=["Gamification"])
router.include_router(stats_router, prefix="/stats", tags=["Platform Statistics"])
router.include_router(locations_router, tags=["Locations"])
router.include_router(ads_router, prefix="/ads", tags=["Ad Engagement"])
router.include_router(
    community_achievements_router,
    prefix="/community-achievements",
    tags=["Community Achievements"],
)
