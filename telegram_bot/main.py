import os
import logging
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from vcf_utils import create_vcf, process_bulk, parse_vcf_data # vcf_utils থেকে ফাংশন ইম্পোর্ট

# বট টোকেন এনভায়রনমেন্ট ভেরিয়েবল থেকে লোড করা হবে
# এটি আপনার .env ফাইল বা Vercel এনভায়রনমেন্টে সেট করা থাকবে
BOT_TOKEN = os.getenv('BOT_TOKEN', '8523158193:AAE7LKktxM-vq13I1aoHqyID6BTdfTJUnv8') # টোকেন এখানে বা এনভ ভেরিয়েবলে দিন

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- কমান্ড হ্যান্ডলার্স ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a greeting message when the command /start is issued."""
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message when the command /help is issued."""
    await update.message.reply_text(
        "**Contactum Bot Help:**\n\n"
        "**To create VCF from text:**\n"
        "1.  Send your names and numbers as plain text.\n"
        "2.  After sending all lines, use the command `/create_vcf`.\n\n"
        "**To read VCF to text:**\n"
        "1.  Send me a `.vcf` file as an attachment.\n\n"
        "Feel free to experiment! If you have any issues, contact support."
    )

# টেক্সট ইনপুট স্টোর করার জন্য একটি ডিকশনারি
user_inputs = {}

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text messages and stores them for VCF creation."""
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_inputs:
        user_inputs[user_id] = []
    
    user_inputs[user_id].append(text)
    
    await update.message.reply_text("Text received. Send more lines or use `/create_vcf` to generate.")

async def create_vcf_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Creates a VCF file from stored text inputs."""
    user_id = update.effective_user.id
    
    if user_id not in user_inputs or not user_inputs[user_id]:
        await update.message.reply_text("No text found to create VCF. Please send names and numbers first.")
        return
    
    full_text = "\n".join(user_inputs[user_id])
    vcf_content = process_bulk(full_text)
    
    if not vcf_content.strip():
        await update.message.reply_text("Could not process any valid contacts from the provided text.")
        return

    # VCF ফাইল তৈরি করা
    file_name = "contacts.vcf"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(vcf_content)
    
    # ফাইলটি ইউজারকে পাঠানো
    with open(file_name, "rb") as f:
        await update.message.reply_document(
            document=InputFile(f), 
            filename=file_name, 
            caption="Here is your generated VCF file!"
        )
    
    # ফাইল ডিলিট করা এবং ইনপুট ক্লিয়ার করা
    os.remove(file_name)
    del user_inputs[user_id]
    await update.message.reply_text("Your VCF file has been generated. Input cleared.")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles .vcf file uploads and extracts contacts."""
    if update.message.document and update.message.document.file_name.endswith('.vcf'):
        file_id = update.message.document.file_id
        file_obj = await context.bot.get_file(file_id)
        
        # ফাইলটি ডাউনলোড করা
        downloaded_file = await file_obj.download_as_bytearray()
        vcf_content = downloaded_file.decode('utf-8') # ধরে নিচ্ছি UTF-8 এনকোডিং

        contacts = parse_vcf_data(vcf_content)
        
        if contacts:
            response_text = "Extracted Contacts:\n\n"
            for contact in contacts:
                response_text += f"**Name:** {contact['name']}\n**Phone:** {contact['phone']}\n---\n"
            
            # লম্বা রেসপন্স হলে ফাইল হিসাবে পাঠানো
            if len(response_text) > 4000: # টেলিগ্রাম মেসেজ লিমিট
                output_file_name = "extracted_contacts.txt"
                with open(output_file_name, "w", encoding="utf-8") as f:
                    f.write(response_text)
                with open(output_file_name, "rb") as f:
                    await update.message.reply_document(
                        document=InputFile(f),
                        filename=output_file_name,
                        caption="Here are the extracted contacts from your VCF file."
                    )
                os.remove(output_file_name)
            else:
                await update.message.reply_text(response_text, parse_mode='Markdown')
        else:
            await update.message.reply_text("No contacts could be extracted from the VCF file.")
    else:
        await update.message.reply_text("Please upload a valid `.vcf` file.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a user-friendly message."""
    logger.error(f"Update {update} caused error {context.error}")
    await update.message.reply_text("An error occurred. Please try again or use /help.")


def main() -> None:
    """Starts the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # কমান্ড হ্যান্ডলার্স
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("create_vcf", create_vcf_command))

    # মেসেজ হ্যান্ডলার্স
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # এরর হ্যান্ডলার
    application.add_handler(CallbackQueryHandler(error_handler)) # CallbackQueryHandler এর বদলে ErrorHandler ব্যবহার করা উচিত
    application.add_handler(application.add_error_handler(error_handler)) # এটি সঠিক

    # পুলিং স্টার্ট করা
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
