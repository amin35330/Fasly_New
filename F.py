import logging
import pandas as pd
import asyncio
import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext

# تنظیمات اولیه برای ورود به فایل اکسل و توکن بات
BOT_TOKEN = '7403744632:AAFbcK2CQPFYVZrCXHF1eISEeNs2Hi0QAUM'
EXCEL_FILE = 'data.xlsx'

# تنظیمات لاگ برای دیباگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# اعمال nest_asyncio
nest_asyncio.apply()

# تابع برای خوش‌آمدگویی و نمایش پیام اولیه
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

# تابع برای ارسال دکمه‌های پروژه‌ها (با صفحه‌بندی)
async def send_project_buttons(update: Update, context: CallbackContext, page=0) -> None:
    df = pd.read_excel(EXCEL_FILE, dtype={'Users': str})  # تعیین نوع ستون 'Users' به عنوان رشته
    start_idx = page * 16
    end_idx = start_idx + 16
    projects = df.iloc[start_idx:end_idx]

    keyboard = []
    row = []
    for idx, row_data in projects.iterrows():
        project_name = row_data['Project']
        user = row_data['Users']
        callback_data = f"project_{start_idx + idx}_{page}"
        if pd.isna(user) or user == 'nan':
            button_text = f"🔵 {project_name}"
        else:
            button_text = f"✅ {project_name} - {user}"
        row.append(InlineKeyboardButton(button_text, callback_data=callback_data))

        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    # افزودن دکمه‌های کنترل صفحه
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

# تابع برای مدیریت کلیک دکمه‌های پروژه‌ها
async def button_click(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    df = pd.read_excel(EXCEL_FILE, dtype={'Users': str})  # تعیین نوع ستون 'Users' به عنوان رشته
    callback_data = query.data

    # بررسی کلیک دکمه‌های صفحه‌بندی
    if callback_data.startswith("page_"):
        page = int(callback_data.split("_")[1])
        await send_project_buttons(update, context, page)
        return

    if callback_data.startswith("project_"):
        project_index, page = map(int, callback_data.split("_")[1:])
        project_name = df.iloc[project_index - page * 16]['Project']
        user_name = query.from_user.username

        # به‌روزرسانی کاربر مربوط به پروژه
        if pd.isna(df.at[project_index - page * 16, 'Users']) or df.at[project_index - page * 16, 'Users'] == 'nan':
            df.at[project_index - page * 16, 'Users'] = user_name
        elif df.at[project_index - page * 16, 'Users'] == user_name:
            df.at[project_index - page * 16, 'Users'] = pd.NA

        df.to_excel(EXCEL_FILE, index=False)
        await send_project_buttons(update, context, page)

# تابع برای انتقال پروژه‌های انجام‌شده به شیت جدید
def move_done_projects() -> None:
    df = pd.read_excel(EXCEL_FILE, dtype={'Users': str})  # تعیین نوع ستون 'Users' به عنوان رشته
    done_projects = df.dropna(subset=['Users'])
    if not done_projects.empty:
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl', mode='a') as writer:
            done_projects.to_excel(writer, sheet_name='Done', index=False, header=not writer.sheets)
        df.drop(done_projects.index, inplace=True)
        df.to_excel(EXCEL_FILE, index=False)

async def main() -> None:
    move_done_projects()

    # ایجاد و تنظیم برنامه تلگرام
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("Start", start))
    application.add_handler(CommandHandler("Fasly", start))
    application.add_handler(CallbackQueryHandler(button_click))

    # شروع polling
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())