# app/interactors/telegram_ai.py
import asyncio
import os
from decimal import Decimal
from datetime import datetime
from typing import List

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dishka import AsyncContainer

from app.core.config import TelegramConfig
from app.interactors.moneyIteractor import MoneyIteractor


class TelegramInteractor:
    def __init__(self, bot_token: str, chat_ids: List[int]):
        self.bot_token = bot_token
        self.chat_ids = chat_ids
        self.bot = Bot(token=self.bot_token, default=DefaultBotProperties(parse_mode="Markdown"))
        self.dp = Dispatcher()
        self._is_running = False
        self._polling_task = None
        self.container: AsyncContainer = None  # Будет установлен в lifespan
        self.card_repository: AsyncContainer = None

        self._register_handlers()

    def set_container(self, container: AsyncContainer):
        """Установка контейнера для получения зависимостей"""
        self.container = container

    def set_container_card(self, container: AsyncContainer):
        self.card_repository = container

    def _register_handlers(self):
        """Регистрация обработчиков callback'ов"""

        @self.dp.callback_query(F.data.startswith("withdraw_confirm_"))
        async def confirm_withdraw(callback: types.CallbackQuery):
            try:
                _, _, user_id, amount_str = callback.data.split("_", 3)
                amount = Decimal(amount_str)

                # Получаем MoneyIteractor из контейнера
                # async with self.container() as request_container:
                #     from app.interactors.moneyIteractor import MoneyIteractor
                #     money_interactor = await request_container.get(MoneyIteractor)
                #     new_balance = await money_interactor.make_withdrawal(user_id, amount)
                    # await money_interactor.set_user_balance(user_id, new_balance.balance)
                # new_caption = f"✅ Вывод *{amount:,.2f} UZS* пользователю `{user_id}` подтвержден."

                # await callback.message.edit_caption(
                #     caption=new_caption,
                #     reply_markup=None  # Убираем кнопки
                # )

                # await callback.answer("Вывод подтвержден")

            except Exception as e:
                await callback.answer(f"Ошибка: {str(e)}")
                print(f"[TelegramInteractor] Confirm withdraw error: {e}")

        # 🔹 Отклонение вывода
        @self.dp.callback_query(F.data.startswith("withdraw_reject_"))
        async def reject_withdraw(callback: types.CallbackQuery):
            try:
                _, _, user_id, amount_str = callback.data.split("_", 3)
                amount = Decimal(amount_str)

                new_caption = f"❌ Запрос на вывод *{amount:,.2f} USD* пользователю `{user_id}` отклонен."
                await callback.message.edit_caption(
                    caption=new_caption,
                    reply_markup=None  # Убираем кнопки
                )

                await callback.answer("Вывод отклонен")

            except Exception as e:
                await callback.answer(f"Ошибка: {str(e)}")
                print(f"[TelegramInteractor] Reject withdraw error: {e}")

        @self.dp.callback_query(F.data.startswith("confirm_"))
        async def confirm_callback(callback: types.CallbackQuery):
            try:
                # Разбираем callback_data: "confirm_{user_id}_{amount}"
                parts = callback.data.split("_")
                if len(parts) != 3:
                    await callback.answer("Неверный формат данных")
                    return

                _, user_id, amount_str = parts
                amount = Decimal(amount_str)

                # Получаем MoneyIteractor из контейнера
                async with self.container() as request_container:
                    from app.interactors.moneyIteractor import MoneyIteractor
                    money_interactor = await request_container.get(MoneyIteractor)
                    await money_interactor.update_balance(user_id, amount)
                    await money_interactor.set_initial_balance(user_id, amount)

                # Редактируем caption сообщения с фото
                new_caption = f"✅ Баланс пользователя {user_id} обновлен на {amount:,} USD"

                # Способ 1: Редактируем только подпись
                await callback.message.edit_caption(
                    caption=new_caption,
                    reply_markup=None  # Убираем кнопки
                )

                await callback.answer("Баланс подтвержден")
                return True

            except Exception as e:
                await callback.answer(f"Ошибка: {str(e)}")
                print(f"Confirm callback error: {e}")

        @self.dp.callback_query(F.data.startswith("reject_"))
        async def reject_callback(callback: types.CallbackQuery):
            try:
                parts = callback.data.split("_")
                if len(parts) != 3:
                    await callback.answer("Неверный формат данных")
                    return

                _, user_id, amount_str = parts

                new_caption = f"❌ Пополнение пользователя {user_id} отклонено"

                await callback.message.edit_caption(
                    caption=new_caption,
                    reply_markup=None  # Убираем кнопки
                )

                await callback.answer("Пополнение отклонено")
                return False

            except Exception as e:
                await callback.answer(f"Ошибка: {str(e)}")
                print(f"Reject callback error: {e}")

        @self.dp.message(F.text.startswith("/set_card"))
        async def set_card_handler(message: types.Message):
            parts = message.text.split()

            # Проверяем что есть как минимум номер карты (16 цифр) и имя
            if len(parts) < 5:  # /set_card + 4 части номера + имя
                await message.reply("⚠️ Используйте формат: `/set_card 1234 5678 9012 3456 Ivan Ivanov`")
                return

            # Извлекаем номер карты (первые 4 части после команды)
            card_parts = parts[1:5]  # ['1234', '5678', '9012', '3456']

            # Проверяем что все части номера карты состоят из цифр
            if not all(part.isdigit() and len(part) == 4 for part in card_parts):
                await message.reply(
                    "❌ Неверный формат номера карты. Используйте: `/set_card 1234 5678 9012 3456 Ivan Ivanov`")
                return

            # Собираем номер карты
            card_number = ' '.join(card_parts)  # '1234 5678 9012 3456'

            # Извлекаем имя (все оставшиеся части)
            name_parts = parts[5:]  # ['Ivan', 'Ivanov']
            card_holder_name = ' '.join(name_parts)  # 'Ivan Ivanov'

            # Проверяем что имя не пустое
            if not card_holder_name.strip():
                await message.reply("❌ Укажите имя владельца карты: `/set_card 1234 5678 9012 3456 Ivan Ivanov`")
                return

            async with self.card_repository() as request_container:
                from app.interactors.cardIteractor import CardIteractor
                card_iteractor = await request_container.get(CardIteractor)
                await card_iteractor.set_bank_card(card_number, card_holder_name)

            await message.reply(f"✅ Данные карты сохранены:\n"
                                f"Номер: `{card_number}`\n"
                                f"Владелец: `{card_holder_name}`")

    async def send_invoice_notification(
            self,
            user_id: str,
            user_email: str,
            amount: Decimal,
            file_path: str,
    ):
        formatted_amount = f"{amount:,.2f} USD"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=f"confirm_{user_id}_{amount}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject_{user_id}_{amount}"
                )
            ]
        ])

        caption_text = (
            f"💰 *НОВОЕ ПОПОЛНЕНИЕ БАЛАНСА*\n\n"
            f"👤 *Пользователь:* {user_id}\n"
            f"📧 *Email:* {user_email}\n"
            f"💵 *Сумма:* {formatted_amount}\n"
            f"⏰ *Время:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        success_count = 0
        for chat_id in self.chat_ids:
            try:

                with open(file_path, "rb") as photo_file:
                    photo = FSInputFile(file_path)
                    await self.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=caption_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )

                success_count += 1
            except Exception as e:
                print(f"Error sending to chat {chat_id}: {e}")
                continue

        return success_count > 0

    async def send_withdraw_notification(
            self,
            user_id: str,
            user_email: str,
            amount: Decimal,
            file_path: str,
            card_number: str,
            full_name: str
    ) -> bool:
        """Отправка уведомления о запросе на вывод средств"""

        formatted_amount = f"{amount:,.2f} USD"

        # keyboard = InlineKeyboardMarkup(
        #     inline_keyboard=[
        #         [
        #             InlineKeyboardButton(
        #                 text="✅ Подтвердить вывод",
        #                 callback_data=f"withdraw_confirm_{user_id}_{amount}"
        #             ),
        #             InlineKeyboardButton(
        #                 text="❌ Отклонить вывод",
        #                 callback_data=f"withdraw_reject_{user_id}_{amount}"
        #             )
        #         ]
        #     ]
        # )

        caption_text = (
            "🏧 *ЧЕК ЗА ВЫВОД СРЕДСТВ*\n\n"
            f"👤 *Пользователь:* `{user_id}` | Full Name: `{full_name}`\n"
            f"📧 *Email:* `{user_email}` | Card Number `{card_number}`\n"
            f"💸 *Сумма:* `{formatted_amount}`\n"
            f"🕒 *Время:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
        )

        success_count = 0
        for chat_id in self.chat_ids:
            try:
                photo = FSInputFile(file_path)
                await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption_text,
                    # reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                success_count += 1

            except Exception as e:
                print(f"❌ Error sending withdraw message to chat {chat_id}: {e}")
                continue

        return success_count > 0

    async def start_polling(self):
        """Запуск бота для обработки callback'ов"""
        if self._is_running:
            print("⚠️ Bot is already running")
            return

        try:
            self._is_running = True
            print("🤖 Starting Telegram bot polling...")

            # Запускаем polling в фоне
            self._polling_task = asyncio.create_task(
                self.dp.start_polling(self.bot)
            )

            print("✅ Telegram bot started successfully")

        except Exception as e:
            self._is_running = False
            print(f"❌ Failed to start bot: {e}")
            raise

    async def stop_polling(self):
        """Остановка бота"""
        if not self._is_running:
            return

        print("🛑 Stopping Telegram bot...")

        self._is_running = False

        # Останавливаем polling
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None

        # Закрываем сессии
        await self.dp.storage.close()
        await self.bot.session.close()

        print("✅ Telegram bot stopped successfully")

    @property
    def is_running(self) -> bool:
        """Проверка запущен ли бот"""
        return self._is_running
