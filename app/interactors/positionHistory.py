from app.database.postgres.models import PositionsHistoryModel
from app.database.repositories.positionHistory import PositionHistoryRepository


class PositionHistoryInteractor:
    def __init__(self, position_repository: PositionHistoryRepository):
        self.position_repository = position_repository

    async def save_position(self, user_id, data):
        position = PositionsHistoryModel(
            user_id=user_id,
            type=data.type,
            amount=data.amount,
            profit=data.profit,
            roi=data.roi
        )

        return await self.position_repository.save_position(position)