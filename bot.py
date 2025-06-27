import os
import logging
import random
import json
import base64
from datetime import datetime
from dotenv import load_dotenv

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import (BotCommand, InlineKeyboardButton, InlineKeyboardMarkup,
                      Update)
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler, ContextTypes)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_NAME = "WishListBot"
creds_b64 = os.getenv("GOOGLE_CREDENTIALS_B64")
creds_json = base64.b64decode(creds_b64).decode('utf-8')
credentials_dict = json.loads(creds_json)

# Setup Google Sheets client
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    credentials_dict, scope
)

gc = gspread.authorize(credentials)
sheet = gc.open(SPREADSHEET_NAME).sheet1  # First sheet


class TableHeaders:
    gift_name = 1
    price = 2
    link = 3
    status = 4


class CellHeaders:
    gift_name = 2
    price = 3
    link = 4
    status = 5
    log = 6


HELLO_MESSAGES = [
    "Привіт {}! О, дивись хто згадав, що треба подарунок! Не хвилюйся, я тут, щоб врятувати твій день (і твою репутацію). Тут — тільки те, що твої близькі реально чекали, а не чергова безглузда дрібничка, яку ти знову забудеш подарувати. Вільні подарунки? Бери швидко, бо поки ти думаєш, хтось уже все відхапав! Твої заброньовані подарунки — це твій маленький секрет, як спроба розпочати дієту з понеділка: краще про це не говорити. Обирай опцію і давай вже щось робити, поки святковий дедлайн не накрив тебе як снігова лавина.",
    "Привіт, {}! О, ти тут. Нарешті. Звісно ж, не тому що згадав про подарунки вчасно — просто зірки стали як треба. Добре, що я тут, бо без мене все закінчилося б черговим носком або блокнотом 'на виріст'. Обирай щось гідне. А краще швидко — конкуренція тут серйозна, і твій кузен уже точно щось забронював.",
    "{}! Вітаю в цьому святковому хаосі. Знову чекав(-ла) до останнього моменту, правда ж? Ну нічого. Я твоя остання надія виглядати людиною, яка хоча б вдає, що піклується. Тут — список бажань, обмежена кількість нервів і ще менше часу. Тож не тупи: обирай і бронюй, поки всі подарунки не розібрали інші 'відповідальні'.",
    "О, {}! Хтось нарешті вирішив подбати про близьких! Або хоча б створити таку ілюзію. Цей список — твій шанс подарувати щось, що справді хочуть. Не що-небудь з найближчого супермаркету, а справжнє 'ого, звідки ти знав(-ла)?!'. Тож обирай уважно. Або наосліп — головне хоч щось забронюй до того, як це зробить твоя двоюрідна тітка з Wi-Fi 2G.",
    "Йо, {}! Нарешті ти тут. І я впевнений(-на), ти в захваті від ідеї знову вигадувати, що подарувати. Не переживай — я зробив за тебе найважче: зібрав бажання тих, кого ти вітаєш. Тобі лишилось лише не провтикати момент. Бо інакше буде як завжди: ти знову даруєш 'універсальну' чашку, і тебе знову проклинають за кулісами.",
    "Привіт, {}! Я не кажу, що ти залишив(-ла) все на останній момент, але... в принципі так і є. На щастя, цей бот — твій рятівник. Усе просто: відкриваєш список, вибираєш подарунок, бронюєш. Мінімум зусиль — максимум враження. Навіть виглядаєш турботливою людиною! Майже як той, хто все спланував заздалегідь (але ми-то знаємо).",
    "Здоров, {}! Не буду брехати — шансів вразити залишилось небагато. Але, з іншого боку, ти вже тут, а це вже крок уперед. Перед тобою список речей, які люди реально хочуть, а не 'вибір із паніки в останній день'. То бери щось, бронюй, і будемо прикидатися, що так і було задумано. Ну серйозно — навіть твій пес більш організований.",
    "Привіт, {}! Так, я знаю, тебе змусило життя, а не натхнення. Але ми тут не для суду — ми для діла. Список бажань уже на місці, твої близькі ще не втратили надію, і якщо все зробиш правильно — можеш навіть зібрати кілька балів до карми. Хоча б спробуй не втратити всі одразу. Подарунки не вибирають себе самі — тисни і дій!",
    "О, {}. Святковий сезон — час радості, любові… і паніки останньої хвилини. Якщо ти тут, значить ти або геній планування, або просто на межі зриву. У будь-якому випадку — молодець, що дійшов(-ла) сюди. Обирай подарунок, який хоч хтось дійсно хоче. Це не твій шанс – це останній шанс. І ще трохи сарказму в подарунок 🎁.",
    "Йой, {}! Тут список мрій, які поки ще можна втілити. Якщо в тебе виникла думка: «Ой, може вже пізно?» — відповідь: так, майже. Але ще є час врятувати ситуацію. Не гальмуй — твоя репутація турботливої людини висить на волосинці. І цей бот — твій останній шанс не подарувати повітря або шоколадку з АЗС.",
    "{}! Ти ж не думав(-ла), що без мене обійдешся? Ось він — список, який може перетворити тебе з 'ой, я щось куплю пізніше' на 'вау, як ти здогадався(-лась)?!'. Не зволікай: кожна секунда — ще одна можливість, що твоя бабця забронює останній нормальний варіант. Дій, бо час — це подарунок, якого ти вже майже не маєш 😉",
]

BOOK_BUTTON_VARIANTS = [
    "✅ Моє!",
    "✅ Забираю!",
    "✅ Хочу. І все.",
    "✅ Бронюю 🔥",
    "✅ Моє. Не чіпай.",
    "✅ Та беру вже...",
    "✅ Це моє!",
    "✅ Ну ок, хай буде",
    "✅ Лишіть мені 😤",
    "✅ Моя прєлєсть!",
]
BOOK_BUTTON_LONG_VARIANTS = [
    "✅ Беру! Бо хтось мусить це зробити",
    "✅ Забираю. І не питайте чому",
    "✅ Моє! Шансів вам більше нема",
    "✅ Бронюю, поки не зламався бот",
    "✅ Вирішено — тепер це моє",
    "✅ Хапаю, бо як не я, то хто?",
    "✅ Я народився, щоб це взяти",
    "✅ Мені треба. Дуже. Не смійтесь",
    "✅ Мої очі це вибрали — все",
    "✅ Та дайте вже сюди той дарунок",
]
CANCEL_BUTTON_VARIANTS = [
    "❌ Передумав",
    "❌ Та ну його",
    "❌ Не хочу вже",
    "❌ Забирайте назад",
    "❌ Це не моє",
    "❌ Я передумав 😐",
    "❌ Було імпульсивно",
    "❌ Нехай буде чужим",
    "❌ Я передумав 🫣",
    "❌ Обійдусь якось",
]
CANCEL_BUTTON_LONG_VARIANTS = [
    "❌ Передумав, це все дурня насправді",
    "❌ Та ну його, знайдеться хтось інший",
    "❌ Не хочу вже, нащо мені цей стрес",
    "❌ Забирайте назад, я передумав(ла)",
    "❌ Це точно не моє, дякую за пропозицію",
    "❌ Я передумав(ла), життя коротке",
    "❌ Було імпульсивно, пробачте мене",
    "❌ Нехай хтось інший тепер мучиться",
    "❌ Я передумав(ла), нерви дорожчі",
    "❌ Обійдусь якось без цього дива",
]

VIEW_BUTTON_VARIANTS = [
    "👀 Погляну",
    "👀 Що це?",
    "👀 Подивлюсь",
    "👀 Перевірю",
    "👀 Гляну",
    "👀 Зазирну",
    "👀 Роздивлюсь",
    "👀 Поглянути",
    "👀 Шо там?",
    "👀 Перевірка",
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user  # Get user info
    user_name = user.full_name if user else "всім"

    keyboard = [
        [
            InlineKeyboardButton("🎁 Що ще лишилось?", callback_data="free"),
            InlineKeyboardButton("🔑 Поглянь, що твоє", callback_data="my_booked"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    hello_message = random.choice(HELLO_MESSAGES)

    await update.message.reply_text(
        hello_message.format(user_name), reply_markup=reply_markup
    )


async def show_free_gifts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = sheet.get_all_records()
    keyboards = []
    names = []
    # Start at 2 to account for header row
    for idx, row in enumerate(data, start=2):
        if not row["status"]:
            names.append(row["gift_name"])
            confirm_button_text = random.choice(BOOK_BUTTON_VARIANTS)
            view_button_text = random.choice(VIEW_BUTTON_VARIANTS)
            keyboards.append(
                [
                    InlineKeyboardButton(view_button_text, url=row["link"]),
                    InlineKeyboardButton(
                        confirm_button_text, callback_data=f"book|{idx}"
                    ),
                ]
            )
    text = (
        "🎉 Тут лежать подарунки, які ще не встигли втекти!"
        if keyboards
        else "🙅‍ Немає вільних подарунків, тримай кулачки!."
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    for name, keyboard in zip(names, keyboards):
        reply_markup = InlineKeyboardMarkup([keyboard])
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🎁 {name}",
            reply_markup=reply_markup,
        )


async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, row_num = query.data.split("|")
    row_num = int(row_num)

    row = sheet.row_values(row_num)
    gift_name = row[TableHeaders.gift_name]

    # Store details in user_data so we can restore later if canceled
    context.user_data["last_gift"] = {
        "row_num": row_num,
        "gift_name": gift_name,
        "price": row[TableHeaders.price],
        "link": row[TableHeaders.link],
    }
    confirm_button_text = random.choice(BOOK_BUTTON_LONG_VARIANTS)
    cancel_button_text = random.choice(CANCEL_BUTTON_LONG_VARIANTS)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    confirm_button_text, callback_data=f"confirm|{row_num}"
                )
            ],
            [InlineKeyboardButton(cancel_button_text, callback_data="cancel")],
        ]
    )

    await query.edit_message_text(
        f"Хочеш забронювати *{gift_name}*? Бо поки ти думаєш, хтось вже пильно спостерігає!",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def finalize_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, row_num = query.data.split("|")
    row_num = int(row_num)
    user_name = query.from_user.full_name

    current_status = sheet.cell(row_num, CellHeaders.status).value
    if current_status and current_status != user_name:
        await query.edit_message_text(
            "❌ Ой, вибач, цей подарунок уже хтось спритний собі приприватив. Швидше наступного шукай!"
        )

    else:
        sheet.update_cell(
            row_num, CellHeaders.status, user_name
        )  # Column 5: status (booked by)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_name = query.from_user.full_name
        log_entry = f"📌 Booked by {user_name} at {timestamp}"

        # Update status
        sheet.update_cell(row_num, CellHeaders.status, user_name)

        # Append to log
        existing_log = sheet.cell(row_num, CellHeaders.log).value or ""
        updated_log = f"{existing_log}\n{log_entry}".strip()

        sheet.update_cell(row_num, CellHeaders.log, updated_log)
        cancel_button_text = random.choice(CANCEL_BUTTON_VARIANTS)

        gift_name = sheet.cell(row_num, CellHeaders.gift_name).value
        view_button_text = random.choice(VIEW_BUTTON_VARIANTS)

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        view_button_text,
                        url=sheet.cell(row_num, CellHeaders.link).value,
                    ),
                    InlineKeyboardButton(
                        cancel_button_text, callback_data=f"unbook|{row_num}"
                    ),
                ]
            ]
        )

        await query.edit_message_text(
            f'✅ Все зроблено — "{gift_name}" тепер під твоїм контролем. Молодець!',
            parse_mode="Markdown",
            reply_markup=keyboard,
        )


async def cancel_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    last = context.user_data.get("last_gift")
    if not last:
        await query.edit_message_text("❌ Скасовано.")
        return

    gift_name = last["gift_name"]
    # price = last["price"]
    link = last["link"]
    row_num = last["row_num"]

    confirm_button_text = random.choice(BOOK_BUTTON_VARIANTS)
    view_button_text = random.choice(VIEW_BUTTON_VARIANTS)

    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(view_button_text, url=link),
                InlineKeyboardButton(
                    confirm_button_text, callback_data=f"book|{row_num}"
                ),
            ]
        ]
    )

    await query.edit_message_text(text=gift_name, reply_markup=reply_markup)


async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        _, row_num = query.data.split("|")
        row_num = int(row_num)
    except ValueError:
        await query.edit_message_text("⚠️ Некоректна дія.")
        return

    user_name = query.from_user.full_name
    current_status = sheet.cell(row_num, CellHeaders.status).value
    gift_name = sheet.cell(row_num, CellHeaders.gift_name).value

    if current_status != user_name:
        await query.edit_message_text(
            "❌ Ой-ой, цей подарунок ти не забронював. Мабуть, плутаєшся у подарунках?"
        )
        return

    # Remove booking
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_name = query.from_user.full_name
    log_entry = f"❌ Unbooked by {user_name} at {timestamp}"

    # Unset booking
    sheet.update_cell(row_num, CellHeaders.status, "")

    # Append to log
    existing_log = sheet.cell(row_num, CellHeaders.log).value or ""
    updated_log = f"{existing_log}\n{log_entry}".strip()

    sheet.update_cell(row_num, CellHeaders.log, updated_log)

    # Restore original "Хочу" button
    link = sheet.cell(row_num, CellHeaders.link).value

    button_text = random.choice(BOOK_BUTTON_VARIANTS)
    view_button_text = random.choice(VIEW_BUTTON_VARIANTS)

    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(view_button_text, url=link),
                InlineKeyboardButton(button_text, callback_data=f"book|{row_num}"),
            ]
        ]
    )

    await query.edit_message_text(text=gift_name, reply_markup=reply_markup)


async def show_booked_gifts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_name = update.message.from_user.full_name
    else:
        query = update.callback_query
        await query.answer()

        user_name = query.from_user.full_name

    data = sheet.get_all_records()
    booked = []
    names = []

    for idx, row in enumerate(data, start=2):
        if row["status"] == user_name:
            names.append(
                row["gift_name"],
            )
            cancel_button_text = random.choice(CANCEL_BUTTON_VARIANTS)
            view_button_text = random.choice(VIEW_BUTTON_VARIANTS)
            booked.append(
                [
                    InlineKeyboardButton(view_button_text, url=row["link"]),
                    InlineKeyboardButton(
                        cancel_button_text, callback_data=f"remove|{idx}"
                    ),
                ]
            )

    text = (
        "Ти справді щось взяв? Вітаю з дивом!"
        if booked
        else "🕵️‍♂️ Твій список подарунків пустий, як твої оправдання."
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    for name, book in zip(names, booked):
        reply_markup = InlineKeyboardMarkup([book])
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🎁 {name}",
            reply_markup=reply_markup,
        )


async def remove_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, row_num = query.data.split("|")
    row_num = int(row_num)

    gift_name = sheet.cell(row_num, CellHeaders.gift_name).value

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Так, скасовую ❌",
                    callback_data=f"remove_confirm|{row_num}",
                ),
                InlineKeyboardButton(
                    "Ні, залишаю 👍", callback_data=f"remove_abort|{row_num}"
                ),
            ]
        ]
    )

    await query.edit_message_text(
        f"⚠️ Ти впевнений, що хочеш скасувати бронювання *{gift_name}*?",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def remove_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, row_num = query.data.split("|")
    row_num = int(row_num)

    user_name = query.from_user.full_name
    current_status = sheet.cell(row_num, CellHeaders.status).value
    gift_name = sheet.cell(row_num, CellHeaders.gift_name).value

    if current_status != user_name:
        await query.edit_message_text(
            f"❌ Цей подарунок *{gift_name}* не твій. Але приємно, що ти спробував!",
            parse_mode="Markdown",
        )
        return

    # Логування зняття броні
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"❌ Unbooked by {user_name} at {timestamp}"

    # Знімаємо бронь
    sheet.update_cell(row_num, CellHeaders.status, "")

    # Оновлюємо лог
    existing_log = sheet.cell(row_num, CellHeaders.log).value or ""
    updated_log = f"{existing_log}\n{log_entry}".strip()
    sheet.update_cell(row_num, CellHeaders.log, updated_log)

    await query.edit_message_text(
        f"✅ Бронювання знято: *{gift_name}*. Ну що ж, ще передумаєш — не дивуйся, якщо його вже не буде 😉",
        parse_mode="Markdown",
    )


async def remove_abort(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, row_num = query.data.split("|")
    row_num = int(row_num)

    gift_name = sheet.cell(row_num, CellHeaders.gift_name).value

    await query.edit_message_text(
        f"👌 Бронювання *{gift_name}* залишилось без змін. Добре подумав!",
        parse_mode="Markdown",
    )


async def set_menu_commands(app):
    await app.bot.set_my_commands(
        [
            BotCommand("start", "📦 Перезапуск місії 'Подарунок'"),
            BotCommand("free", "🎁 Подарунки, які ще не вкрали"),
            BotCommand("my_booked", "🔒 Mої трофеї"),
        ]
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cmd = query.data
    if cmd == "free":
        await show_free_gifts(update, context=context)
    elif cmd == "my_booked":
        await show_booked_gifts(update, context=context)

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = "https://wishlist-telegram-bot.onrender.com" + WEBHOOK_PATH

import inspect
from telegram.ext import Application

print(inspect.signature(Application.run_webhook))
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
# app = (
#     ApplicationBuilder()
#     .token(TELEGRAM_BOT_TOKEN)
#     .webhook(
#         listen="0.0.0.0",
#         port=443,
#         url_path=WEBHOOK_PATH,
#         webhook_url=WEBHOOK_URL
#     )
#     .build()
# )
# Add this line to set menu commands at startup
app.post_init = set_menu_commands
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("free", show_free_gifts))
app.add_handler(CommandHandler("my_booked", show_booked_gifts))
app.add_handler(CallbackQueryHandler(confirm_booking, pattern="^book\\|"))
app.add_handler(CallbackQueryHandler(finalize_booking, pattern="^confirm\\|"))
app.add_handler(CallbackQueryHandler(remove_booking, pattern="^remove\\|"))
app.add_handler(CallbackQueryHandler(cancel_confirmation, pattern="^cancel$"))
app.add_handler(CallbackQueryHandler(cancel_booking, pattern="^unbook\\|"))
app.add_handler(CallbackQueryHandler(remove_confirm, pattern=r"^remove_confirm\|"))
app.add_handler(CallbackQueryHandler(remove_abort, pattern=r"^remove_abort\|"))
app.add_handler(CallbackQueryHandler(button_handler))


# async def main():
#     app.run_webhook(
#         listen="0.0.0.0",          # listen on all IPs
#         port=443,                 # port to listen on
#         webhook_url=WEBHOOK_URL,
#         # webhook_path=WEBHOOK_PATH,
#         # secret_token="your_secret_token"  # optional, but recommended
#     )

if __name__ == "__main__":
    # app.run_webhook()
    app.run_webhook(
        listen="0.0.0.0",          # listen on all IPs
        port=443,                 # port to listen on
        webhook_url=WEBHOOK_URL,
        url_path=WEBHOOK_PATH,  # Шлях, на який Telegram надсилатиме POST
        # webhook_path=WEBHOOK_PATH,
        # secret_token="your_secret_token"  # optional, but recommended
    )
    # import asyncio
    # asyncio.run(main())
#
# if __name__ == "__main__":
#     app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
#
#     # Add this line to set menu commands at startup
#     app.post_init = set_menu_commands
#
#     app.add_handler(CommandHandler("start", start))
#     app.add_handler(CommandHandler("free", show_free_gifts))
#     app.add_handler(CommandHandler("my_booked", show_booked_gifts))
#     app.add_handler(CallbackQueryHandler(confirm_booking, pattern="^book\\|"))
#     app.add_handler(CallbackQueryHandler(finalize_booking, pattern="^confirm\\|"))
#     app.add_handler(CallbackQueryHandler(remove_booking, pattern="^remove\\|"))
#     app.add_handler(CallbackQueryHandler(cancel_confirmation, pattern="^cancel$"))
#     app.add_handler(CallbackQueryHandler(cancel_booking, pattern="^unbook\\|"))
#     app.add_handler(CallbackQueryHandler(remove_confirm, pattern=r"^remove_confirm\|"))
#     app.add_handler(CallbackQueryHandler(remove_abort, pattern=r"^remove_abort\|"))
#     app.add_handler(CallbackQueryHandler(button_handler))
#
#     # Start polling
#     app.run_polling()
