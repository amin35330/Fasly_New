import os
import logging
import pandas as pd
import asyncio
import nest_asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext

# ====================
# تنظیمات اولیه
# ====================
BOT_TOKEN = '7403744632:AAFbcK2CQPFYVZrCXHF1eISEeNs2Hi0QAUM'
EXCEL_FILE = 'data.xlsx'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# اعمال nest_asyncio برای حل مشکلات event loop
nest_asyncio.apply()

# ====================
# بخش تلگرام
# ====================

# تابع شروع برای نمایش پیام خوش‌آمدگویی و ارسال دکمه‌های پروژه‌ها
async def start(update: Update, context: CallbackContext) -> None:
    welcome_message = (
        "همکاران عزیز و گرامی ☘️  \n"
        "احتراماً لیست زیر، اسامی مجموعه‌هایی است که می‌بایست به آن‌ها خدمات فصلی ارائه گردد."
        " خواهشمند است هر یک از شما عزیزان که خدمات فصلی را انجام می‌دهید، چه آن خدمات فصلی توسط"
        " برنامه‌ریزی برای شما تنظیم شده باشد و چه خودتان از این لیست برداشت کرده باشید، می‌بایست بر"
        " روی دکمه مربوط به آن پروژه کلیک کنید تا نام کاربری شما در کنار نام پروژه قرار گیرد.  \n"
        "برای فراخوانی این لیست هر زمان که نیاز داشتید /Fasly را ارسال نمایید.  \n"
        "با سپاس از همراهی شما 🙏🌺"
    )
    await update.message.reply_text(welcome_message)
    await send_project_buttons(update, context)

# تابع ارسال دکمه‌های پروژه با صفحه‌بندی
async def send_project_buttons(update: Update, context: CallbackContext, page=0) -> None:
    df = pd.read_excel(EXCEL_FILE, dtype={'Users': str})
    start_idx = page * 16
    end_idx = start_idx + 16
    projects = df.iloc[start_idx:end_idx]

    keyboard = []
    row_buttons = []
    for idx, row_data in projects.iterrows():
        project_name = row_data['Project']
        user = row_data['Users']
        callback_data = f"project_{start_idx + idx}_{page}"
        if pd.isna(user) or user == 'nan':
            button_text = f"🔵 {project_name}"
        else:
            button_text = f"✅ {project_name} - {user}"
        row_buttons.append(InlineKeyboardButton(button_text, callback_data=callback_data))

        if len(row_buttons) == 2:
            keyboard.append(row_buttons)
            row_buttons = []

    if row_buttons:
        keyboard.append(row_buttons)

    # افزودن دکمه‌های ناوبری صفحات
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton("⬅️ صفحه قبلی", callback_data=f"page_{page - 1}"))
    if end_idx < len(df):
        navigation_buttons.append(InlineKeyboardButton("صفحه بعدی ➡️", callback_data=f"page_{page + 1}"))
    if navigation_buttons:
        keyboard.append(navigation_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("لیست پروژه‌ها:", reply_markup=reply_markup)
    else:
        await update.callback_query.message.edit_reply_markup(reply_markup)

# مدیریت کلیک دکمه‌ها
async def button_click(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    df = pd.read_excel(EXCEL_FILE, dtype={'Users': str})
    callback_data = query.data

    # اگر دکمه صفحه‌بندی فشرده شد
    if callback_data.startswith("page_"):
        page = int(callback_data.split("_")[1])
        await send_project_buttons(update, context, page)
        return

    if callback_data.startswith("project_"):
        parts = callback_data.split("_")
        project_index = int(parts[1])
        page = int(parts[2])
        df_index = project_index - page * 16
        project_name = df.iloc[df_index]['Project']
        user_name = query.from_user.username

        # به‌روزرسانی کاربر مربوط به پروژه
        if pd.isna(df.at[df_index, 'Users']) or df.at[df_index, 'Users'] == 'nan':
            df.at[df_index, 'Users'] = user_name
        elif df.at[df_index, 'Users'] == user_name:
            df.at[df_index, 'Users'] = pd.NA

        df.to_excel(EXCEL_FILE, index=False)
        await send_project_buttons(update, context, page)

# انتقال پروژه‌های انجام شده به شیت جدید
def move_done_projects() -> None:
    df = pd.read_excel(EXCEL_FILE, dtype={'Users': str})
    done_projects = df.dropna(subset=['Users'])
    if not done_projects.empty:
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl', mode='a') as writer:
            done_projects.to_excel(writer, sheet_name='Done', index=False, header=not writer.sheets)
        df.drop(done_projects.index, inplace=True)
        df.to_excel(EXCEL_FILE, index=False)

# ====================
# بخش وب سرور (برای باز بودن پورت در Render)
# ====================

async def start_web_server():
    app = web.Application()
    # یک endpoint ساده برای پاسخ دادن به درخواست‌های ورودی
    app.router.add_get('/', lambda request: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 5000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Web server started on port {port}")

# ====================
# تابع اصلی
# ====================

async def main() -> None:
    # انتقال پروژه‌های انجام شده به شیت جدید
    move_done_projects()

    # راه‌اندازی سرور وب به عنوان یک تسک پس‌زمینه (برای باز بودن پورت مورد نیاز Render)
    asyncio.create_task(start_web_server())

    # ایجاد و پیکربندی اپلیکیشن تلگرام
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("Start", start))
    application.add_handler(CommandHandler("Fasly", start))
    application.add_handler(CallbackQueryHandler(button_click))

    # شروع polling برای دریافت پیام‌ها
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
