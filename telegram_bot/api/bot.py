import os
import logging
import json
from flask import Flask, request, Response
from telegram import Update, Bot
from telegram.ext import Dispatcher, MessageHandler, CommandHandler, filters, CallbackQueryHandler

# vcf_utils থেকে ফাংশন ইম্পোর্ট
from vcf_utils import create_vcf, process_bulk, parse_vcf_data

# বট টোকেন এনভায়রনমেন্ট ভেরিয়েবল থেকে লোড করা
BOT_TOKEN = os.getenv('BOT_TOKEN') # এটি Vercel এনভ ভেরিয়েবলে সেট করা থাকবে

# Webhook URL (আপনার Vercel অ্যাপের URL হবে)
WEBHOOK_URL_PATH = "/webhook" # এটি আপনার Vercel ফাংশনের পাথ হবে

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True) # ContextTypes.DEFAULT_TYPE এর জন্য use_context=True

# --- Bot Handlers (আপনার আগের main.py থেকে) ---
user_inputs = {}

async def start(update: Update, context) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"Hi {user.mention_html()}! 👋\n"
        "Welcome to **Contactum** bot!\n\n"
        "I can help you convert text to VCF files and vice versa.\n\n"
        "**Here's what I can do:**\n"
        "1.  **Text to VCF:** Send me names and numbers (one per line, or a bulk list).\n"
        "    Example:\n"
        "    `Sharmin 017xxxxxxxx`\n"
        "    `My Friend +88018xxxxxxxx`\n"
        "    `• A person 016xxxxxxxx`\n"
        "    Then send `/create_vcf` to generate the VCF file.\n\n"
        "2.  **VCF to Text:** Send me a `.vcf` file, and I'll extract the names and numbers for you.\n\n"
        "Try it out! 😊"
    )

async def help_command(update: Update, context) -> None:
    await update.message.reply_text(
        "**Contactum Bot Help:**\n\n"
        "**To create VCF from text:**\n"
        "1.  Send your names and numbers as plain text.\n"
        "2.  After sending all lines, use the command `/create_vcf`.\n\n"
        "**To read VCF to text:**\n"
        "1.  Send me a `.vcf` file as an attachment.\n\n"
        "Feel free to experiment! If you have any issues, contact support."
    )

async def handle_text_input(update: Update, context) -> None:
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_inputs:
        user_inputs[user_id] = []
    
    user_inputs[user_id].append(text)
    
    await update.message.reply_text("Text received. Send more lines or use `/create_vcf` to generate.")

async def create_vcf_command(update: Update, context) -> None:
    user_id = update.effective_user.id
    
    if user_id not in user_inputs or not user_inputs[user_id]:
        await update.message.reply_text("No text found to create VCF. Please send names and numbers first.")
        return
    
    full_text = "\n".join(user_inputs[user_id])
    vcf_content = process_bulk(full_text)
    
    if not vcf_content.strip():
        await update.message.reply_text("Could not process any valid contacts from the provided text.")
        return

    file_name = f"contacts_{user_id}.vcf" # Unique filename for each user
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(vcf_content)
    
    with open(file_name, "rb") as f:
        await update.message.reply_document(
            document=InputFile(f), 
            filename="contacts.vcf", # User will see this name
            caption="Here is your generated VCF file!"
        )
    
    os.remove(file_name)
    del user_inputs[user_id]
    await update.message.reply_text("Your VCF file has been generated. Input cleared.")

async def handle_document(update: Update, context) -> None:
    if update.message.document and update.message.document.file_name.endswith('.vcf'):
        file_id = update.message.document.file_id
        file_obj = await context.bot.get_file(file_id)
        
        # Download the file to a temporary location or in-memory
        # Vercel serverless functions are ephemeral, so temp files are fine.
        temp_file_path = f"/tmp/{update.message.document.file_name}"
        await file_obj.download_to_drive(temp_file_path) # Changed to async download

        with open(temp_file_path, "r", encoding="utf-8") as f:
            vcf_content = f.read()
        os.remove(temp_file_path) # Clean up temp file

        contacts = parse_vcf_data(vcf_content)
        
        if contacts:
            response_text = "Extracted Contacts:\n\n"
            for contact in contacts:
                response_text += f"**Name:** {contact['name']}\n**Phone:** {contact['phone']}\n---\n"
            
            if len(response_text) > 4000:
                output_file_name = f"/tmp/extracted_contacts_{update.effective_user.id}.txt"
                with open(output_file_name, "w", encoding="utf-8") as f:
                    f.write(response_text)
                with open(output_file_name, "rb") as f:
                    await update.message.reply_document(
                        document=InputFile(f),
                        filename="extracted_contacts.txt",
                        caption="Here are the extracted contacts from your VCF file."
                    )
                os.remove(output_file_name)
            else:
                await update.message.reply_text(response_text, parse_mode='Markdown')
        else:
            await update.message.reply_text("No contacts could be extracted from the VCF file.")
    else:
        await update.message.reply_text("Please upload a valid `.vcf` file.")

async def error_handler(update: Update, context) -> None:
    logger.error(f"Update {update} caused error {context.error}")
    if update.effective_message:
        await update.effective_message.reply_text("An error occurred. Please try again or use /help.")

# Add handlers to dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(CommandHandler("create_vcf", create_vcf_command))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
dispatcher.add_handler(MessageHandler(filters.Document.ALL, handle_document))
dispatcher.add_error_handler(error_handler)


@app.route(WEBHOOK_URL_PATH, methods=["POST"])
async def webhook_handler():
    """Handle incoming Telegram updates."""
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        # Process the update asynchronously
        await dispatcher.process_update(update)
    return Response("ok", status=200)

@app.route("/", methods=["GET"])
def index():
    return "Contactum Telegram Bot is running via Webhook!"

# For local testing, you might need to set webhook first
# async def setup_webhook():
#    webhook_url = f"YOUR_VERCEL_APP_URL{WEBHOOK_URL_PATH}"
#    await bot.set_webhook(url=webhook_url)
#    logger.info(f"Webhook set to {webhook_url}")

# if __name__ == "__main__":
#    # Run this locally for testing or to set webhook once
#    # import asyncio
#    # asyncio.run(setup_webhook())
#    app.run(port=5000) # For local testing only
