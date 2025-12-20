# app/database/init_db.py

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def init_database(engine: AsyncEngine):
    """
    Автоматическая инициализация схемы БД при старте приложения

    ✅ Создает таблицы если не существуют
    ✅ Добавляет поля если не существуют
    ✅ Создает индексы если не существуют
    ✅ НЕ УДАЛЯЕТ и НЕ ИЗМЕНЯЕТ существующие данные
    ✅ Идемпотентная операция (можно запускать многократно)
    """

    async with engine.begin() as conn:
        try:
            # ========== 1. ТАБЛИЦА ПРОМОКОДОВ ==========
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS promo_codes (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    code VARCHAR(50) UNIQUE NOT NULL,
                    bonus_percent INTEGER NOT NULL CHECK (bonus_percent > 0 AND bonus_percent <= 100),
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    max_uses INTEGER DEFAULT NULL,
                    current_uses INTEGER DEFAULT 0 NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP DEFAULT NULL
                );
            """))
            print("  ✓ promo_codes table checked")

            # Индекс для быстрого поиска по коду
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_promo_codes_code 
                ON promo_codes(code);
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_promo_codes_active 
                ON promo_codes(is_active);
            """))
            print("  ✓ promo_codes indexes checked")

            # ========== 2. ТАБЛИЦА ИСТОРИИ ИСПОЛЬЗОВАНИЯ ПРОМОКОДОВ ==========
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_promo_code_usage (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    promo_code_id UUID NOT NULL REFERENCES promo_codes(id) ON DELETE CASCADE,
                    used_at TIMESTAMP DEFAULT NOW(),
                    bonus_amount NUMERIC(15, 2) NOT NULL,
                    UNIQUE(user_id)
                );
            """))
            print("  ✓ user_promo_code_usage table checked")

            # Индексы для оптимизации запросов
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_promo_usage_user 
                ON user_promo_code_usage(user_id);
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_promo_usage_promo 
                ON user_promo_code_usage(promo_code_id);
            """))
            print("  ✓ user_promo_code_usage indexes checked")

            # ========== 3. ДОБАВЛЕНИЕ ПОЛЕЙ В ТАБЛИЦУ USERS ==========
            await conn.execute(text("""
                DO $$ 
                BEGIN
                    -- Промокод использованный при регистрации
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='users' AND column_name='promo_code_used'
                    ) THEN
                        ALTER TABLE users ADD COLUMN promo_code_used VARCHAR(50) DEFAULT NULL;
                        RAISE NOTICE 'Added column promo_code_used to users';
                    END IF;

                    -- Процент бонуса от промокода
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='users' AND column_name='registration_promo_percent'
                    ) THEN
                        ALTER TABLE users ADD COLUMN registration_promo_percent INTEGER DEFAULT 0;
                        RAISE NOTICE 'Added column registration_promo_percent to users';
                    END IF;

                    -- Сумма полученного бонуса
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='users' AND column_name='promo_bonus_received'
                    ) THEN
                        ALTER TABLE users ADD COLUMN promo_bonus_received NUMERIC(15, 2) DEFAULT 0.00;
                        RAISE NOTICE 'Added column promo_bonus_received to users';
                    END IF;
                END $$;
            """))
            print("  ✓ users table columns checked")

            # Индекс для поиска пользователей с промокодами
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_promo_code 
                ON users(promo_code_used) 
                WHERE promo_code_used IS NOT NULL;
            """))
            print("  ✓ users indexes checked")

            print("✅ Database schema initialized successfully")

        except Exception as e:
            print(f"❌ Error initializing database schema: {e}")
            raise


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

async def check_database_health(engine: AsyncEngine) -> dict:
    """
    Проверка состояния БД и наличия всех необходимых структур
    """
    async with engine.connect() as conn:
        results = {}

        # Проверка таблиц
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('promo_codes', 'user_promo_code_usage', 'users');
        """))
        tables = [row[0] for row in result]
        results['tables'] = {
            'promo_codes': 'promo_codes' in tables,
            'user_promo_code_usage': 'user_promo_code_usage' in tables,
            'users': 'users' in tables
        }

        # Проверка полей в users
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name IN ('promo_code_used', 'registration_promo_percent', 'promo_bonus_received');
        """))
        columns = [row[0] for row in result]
        results['user_columns'] = {
            'promo_code_used': 'promo_code_used' in columns,
            'registration_promo_percent': 'registration_promo_percent' in columns,
            'promo_bonus_received': 'promo_bonus_received' in columns
        }

        # Проверка количества промокодов
        result = await conn.execute(text("SELECT COUNT(*) FROM promo_codes;"))
        promo_count = result.scalar()
        results['promo_codes_count'] = promo_count

        return results


async def reset_promo_codes(engine: AsyncEngine):
    """
    ⚠️ ОПАСНО! Удаляет все промокоды (НЕ пользовательские данные)
    Используйте только для тестирования
    """
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE user_promo_code_usage CASCADE;"))
        await conn.execute(text("DELETE FROM promo_codes;"))
        print("⚠️ Promo codes reset")