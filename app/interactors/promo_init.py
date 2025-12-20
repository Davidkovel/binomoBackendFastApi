from sqlalchemy.ext.asyncio import AsyncSession


async def create_default_promo_codes(session: AsyncSession, repo_class):
    """Создание промокодов по умолчанию"""

    repo = repo_class(session)

    promo_codes = [
        {"code": "FINOVA20", "bonus_percent": 20, "max_uses": None},
        {"code": "FINOVA30", "bonus_percent": 30, "max_uses": None},
        {"code": "FINOVA40", "bonus_percent": 40, "max_uses": None},
        {"code": "WELCOME25", "bonus_percent": 25, "max_uses": None},
        {"code": "VIP50", "bonus_percent": 50, "max_uses": None},
    ]

    for promo_data in promo_codes:
        try:
            await repo.create_promo_code(**promo_data)
            print(f"✅ Промокод {promo_data['code']} создан (+{promo_data['bonus_percent']}%)")
        except Exception as e:
            # Игнорируем ошибки дубликатов
            if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
                print(f"ℹ️  Промокод {promo_data['code']} уже существует")
            else:
                print(f"❌ Ошибка при создании {promo_data['code']}: {e}")