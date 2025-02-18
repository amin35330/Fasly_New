import os
import logging
import pandas as pd
import asyncio
import nest_asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from telegram.error import BadRequest

# تنظیمات اولیه
BOT_TOKEN = "7403744632:AAFbcK2CQPFYVZrCXHF1eISEeNs2Hi0QAUM"
EXCEL_FILE = "data.xlsx"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

nest_asyncio.apply()

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
        
        button_text = f"✅ {project_name} - {user}" if pd.notna(user) and user != "nan" else f"🔵 {project_name}"
        row_buttons.append(InlineKeyboardButton(button_text, callback_data=callback_data))

        if len(row_buttons) == 2:
            keyboard.append(row_buttons)
            row_buttons = []

    if row_buttons:
        keyboard.append(row_buttons)

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

        df.at[df_index, "Users"] = user_name if pd.isna(df.at[df_index, "Users"]) or df.at[df_index, "Users"] == "nan" else pd.NA
        df.to_excel(EXCEL_FILE, index=False)
        await send_project_buttons(update, context, page)

async def error_handler(update: object, context: CallbackContext) -> None:
    logger.error(f"خطای بات: {context.error}")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', lambda request: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 5000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Web server started on port {port}")

async def main() -> None:
    asyncio.create_task(start_web_server())

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", send_project_buttons))
    application.add_handler(CommandHandler("projects", send_project_buttons))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_error_handler(error_handler)

    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
