from sqlalchemy import select, UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres.models import PositionsHistoryModel


class PositionHistoryRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_positions_for_user(self, user_id: UUID):
        query = (
            select(PositionsHistoryModel)
            .where(PositionsHistoryModel.user_id == user_id)
            .order_by(PositionsHistoryModel.created_at.desc())
        )

        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def save_position(self, position: PositionsHistoryModel):
        self.db_session.add(position)
        await self.db_session.commit()
        return position