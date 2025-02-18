import os
import logging
import pandas as pd
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from telegram.error import BadRequest

# تنظیمات اولیه
BOT_TOKEN = os.getenv("7403744632:AAFbcK2CQPFYVZrCXHF1eISEeNs2Hi0QAUM")
EXCEL_FILE = "data.xlsx"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# تابع ارسال لیست پروژه‌ها با صفحه‌بندی
async def send_project_buttons(update: Update, context: CallbackContext, page=0) -> None:
    df = pd.read_excel(EXCEL_FILE, dtype={"Users": str})
    projects_per_page = 16
    total_pages = (len(df) // projects_per_page) + (1 if len(df) % projects_per_page > 0 else 0)

    start_idx = page * projects_per_page
    end_idx = start_idx + projects_per_page
    projects = df.iloc[start_idx:end_idx]

    keyboard = []
    row_buttons = []

    for idx, row_data in projects.iterrows():
        project_name = row_data["Project"]
        user = row_data["Users"]
        callback_data = f"project_{start_idx + idx}_{page}"

        if pd.isna(user) or user == "nan":
            button_text = f"🔵 {project_name}"
        else:
            button_text = f"✅ {project_name} - {user}"

        row_buttons.append(InlineKeyboardButton(button_text, callback_data=callback_data))

        if len(row_buttons) == 2:
            keyboard.append(row_buttons)
            row_buttons = []

    if row_buttons:
        keyboard.append(row_buttons)

    # دکمه‌های ناوبری
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton("⏮", callback_data="page_0"))
        navigation_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"page_{page - 1}"))

    if page < total_pages - 1:
        navigation_buttons.append(InlineKeyboardButton("➡️", callback_data=f"page_{page + 1}"))
        navigation_buttons.append(InlineKeyboardButton("⏭", callback_data=f"page_{total_pages - 1}"))

    if navigation_buttons:
        keyboard.append(navigation_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.message:
            await update.message.reply_text("لیست پروژه‌ها:", reply_markup=reply_markup)
        else:
            await update.callback_query.message.edit_reply_markup(reply_markup)
    except BadRequest as e:
        logger.warning(f"خطای ویرایش پیام: {e}")


# تابع مدیریت کلیک دکمه‌ها
async def button_click(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    df = pd.read_excel(EXCEL_FILE, dtype={"Users": str})
    callback_data = query.data

    if callback_data.startswith("page_"):
        page = int(callback_data.split("_")[1])
        await send_project_buttons(update, context, page)
        return

    if callback_data.startswith("project_"):
        parts = callback_data.split("_")
        project_index = int(parts[1])
        page = int(parts[2])
        df_index = project_index - page * 16
        project_name = df.iloc[df_index]["Project"]
        user_name = query.from_user.username

        if pd.isna(df.at[df_index, "Users"]) or df.at[df_index, "Users"] == "nan":
            df.at[df_index, "Users"] = user_name
        elif df.at[df_index, "Users"] == user_name:
            df.at[df_index, "Users"] = pd.NA

        df.to_excel(EXCEL_FILE, index=False)
        await send_project_buttons(update, context, page)


# خطایاب برای جلوگیری از کرش کردن بات
async def error_handler(update: object, context: CallbackContext) -> None:
    logger.error(f"خطای بات: {context.error}")


# وب سرور برای webhook (جایگزین polling)
async def start_web_server(application):
    app = web.Application()
    app.router.add_post(f"/{BOT_TOKEN}", application.update_queue.put)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 5000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Webhook server started on port {port}")


# تابع اصلی اجرا کننده بات
async def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", send_project_buttons))
    application.add_handler(CommandHandler("projects", send_project_buttons))
    application.add_handler(CallbackQueryHandler(button_click))

    application.add_error_handler(error_handler)

    # تنظیم webhook
    webhook_url = f"https://your_domain.com/{BOT_TOKEN}"
    await application.bot.set_webhook(webhook_url)

    await start_web_server(application)

    logger.info("Bot is running...")
    await asyncio.Event().wait()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
