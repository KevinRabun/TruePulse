"""
Seed script to create initial polls for development/demo.
Run with: python -m scripts.seed_polls
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.config import settings
from models.poll import Poll, PollChoice, PollStatus


SEED_POLLS = [
    {
        "question": "Should remote work become the standard for office jobs?",
        "category": "Workplace",
        "source_event": "Remote Work Trends 2025",
        "choices": [
            "Yes, fully remote",
            "Hybrid model is best",
            "No, in-office is better",
            "Depends on the job",
        ],
        "duration_hours": 24,
    },
    {
        "question": "How should AI technology be regulated?",
        "category": "Technology",
        "source_event": "AI Regulation Debates 2025",
        "choices": [
            "Strict government oversight",
            "Industry self-regulation",
            "Minimal regulation",
            "International coordination",
            "Undecided",
        ],
        "duration_hours": 24,
    },
    {
        "question": "What is the most effective way to combat climate change?",
        "category": "Environment",
        "source_event": "COP30 Climate Summit",
        "choices": [
            "Government regulations",
            "Corporate responsibility",
            "Individual action",
            "Technological innovation",
        ],
        "duration_hours": 24,
    },
    {
        "question": "Should social media platforms be required to verify user identities?",
        "category": "Technology",
        "source_event": "Online Safety Legislation",
        "choices": [
            "Yes, for all users",
            "Yes, but optional",
            "No, privacy is more important",
            "Only for public figures",
        ],
        "duration_hours": 24,
    },
    {
        "question": "What should be the priority for healthcare spending?",
        "category": "Health",
        "source_event": "Healthcare Reform Bill",
        "choices": [
            "Preventive care",
            "Mental health services",
            "Emergency services",
            "Research and development",
        ],
        "duration_hours": 24,
    },
    {
        "question": "Should there be a universal basic income?",
        "category": "Economy",
        "source_event": "Economic Policy Forum",
        "choices": [
            "Yes, for everyone",
            "Yes, but means-tested",
            "No, it disincentivizes work",
            "Need more research",
        ],
        "duration_hours": 24,
    },
]


async def seed_polls():
    """Create seed polls in the database."""
    engine = create_async_engine(settings.POSTGRES_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if polls already exist
        result = await session.execute(select(Poll).limit(1))
        existing = result.scalar_one_or_none()
        
        if existing:
            print("Polls already exist in database. Skipping seed.")
            return

        now = datetime.now(timezone.utc)
        
        for i, poll_data in enumerate(SEED_POLLS):
            # First poll is active, rest are scheduled
            if i == 0:
                status = PollStatus.ACTIVE
                scheduled_start = now - timedelta(hours=1)
                scheduled_end = now + timedelta(hours=poll_data["duration_hours"])
                expires_at = scheduled_end
            else:
                status = PollStatus.SCHEDULED
                # Schedule subsequent polls
                scheduled_start = now + timedelta(hours=i * poll_data["duration_hours"])
                scheduled_end = scheduled_start + timedelta(hours=poll_data["duration_hours"])
                expires_at = scheduled_end
            
            poll = Poll(
                id=str(uuid.uuid4()),
                question=poll_data["question"],
                category=poll_data["category"],
                source_event=poll_data["source_event"],
                status=status.value,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                expires_at=expires_at,
                duration_hours=poll_data["duration_hours"],
                is_featured=(i < 2),  # First two are featured
                ai_generated=True,
            )
            
            # Add choices
            for order, choice_text in enumerate(poll_data["choices"]):
                choice = PollChoice(
                    id=str(uuid.uuid4()),
                    poll_id=poll.id,
                    text=choice_text,
                    order=order,
                    vote_count=0,
                )
                poll.choices.append(choice)
            
            session.add(poll)
            print(f"Created poll: {poll_data['question'][:50]}... ({status})")
        
        await session.commit()
        print(f"\n✅ Created {len(SEED_POLLS)} polls successfully!")


if __name__ == "__main__":
    asyncio.run(seed_polls())
