import os
import re
from io import BytesIO
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

# --- VCF Utility Functions (আপনার আগের স্ক্রিপ্ট থেকে) ---
def format_number(num_str):
    bengali_digits = "০১২৩৪৫৬৭৮৯"
    english_digits = "0123456789"
    for b, e in zip(bengali_digits, english_digits):
        num_str = num_str.replace(b, e)
    clean_num = re.sub(r'\D', '', num_str)
    if clean_num.startswith('880'):
        clean_num = clean_num[2:]
    if clean_num.startswith('0'):
        return f"+88{clean_num}"
    else:
        return f"+880{clean_num}"

def create_vcf_string(name, phone):
    formatted_phone = format_number(phone)
    vcf_template = f"BEGIN:VCARD\nVERSION:2.1\nN:{name};;;\nTEL;CELL;PREF:{formatted_phone}\nEND:VCARD"
    return vcf_template

def process_text_to_vcf_bulk(text):
    lines = re.split(r'\n', text)
    results = []
    
    for line in lines:
        if not line.strip(): continue
        clean_line = re.sub(r'[•°:>]', ' ', line).strip()
        phones = re.findall(r'(?:\+?88)?01[3-9]\d{8}', clean_line)
        
        if phones:
            phone = phones[0]
            name = clean_line.replace(phone, '').strip()
            if not name: name = "No Name"
            results.append(create_vcf_string(name, phone))
    
    return "\n".join(results)

# --- Reverse VCF functions ---
def parse_vcf_string(vcf_content):
    contacts = []
    current_contact = {}
    lines = vcf_content.splitlines()

    for line in lines:
        if line.startswith("BEGIN:VCARD"):
            current_contact = {}
        elif line.startswith("N:"):
            # N:LastName;FirstName;MiddleName;Prefix;Suffix
            parts = line[2:].split(';')
            first_name = parts[1] if len(parts) > 1 else ""
            last_name = parts[0] if len(parts) > 0 else ""
            current_contact['name'] = f"{first_name} {last_name}".strip()
        elif line.startswith("TEL;"):
            # TEL;TYPE=CELL;VALUE=VOICE:+88017xxxxxxxx
            match = re.search(r'\d+', line) # Find first sequence of digits
            if match:
                phone_number = match.group(0)
                current_contact['phone'] = phone_number
        elif line.startswith("END:VCARD"):
            if 'name' in current_contact and 'phone' in current_contact:
                contacts.append(current_contact)
            current_contact = {} # Reset for next contact
    return contacts

# --- Telegram Bot Handlers ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("Error: BOT_TOKEN environment variable not set.")
    # Fallback for local testing or if you explicitly want to hardcode for testing
    # BOT_TOKEN = "YOUR_HARDCODED_BOT_TOKEN_HERE" 

bot = Bot(token=BOT_TOKEN)

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'নমস্কার! 👋 Contactum বট আপনাকে স্বাগতম!\n'
        'আমি আপনার টেক্সট থেকে VCF ফাইল তৈরি করতে অথবা VCF ফাইল থেকে কন্টাক্ট ইনফো এক্সট্রাক্ট করতে সাহায্য করব।\n\n'
        'ব্যবহারবিধি:\n'
        '১. 📞 কন্টাক্ট তৈরি করতে: নাম এবং নম্বর লিখুন (প্রতি লাইনে একটি করে)।\n'
        '   যেমন:\n'
        '   `রহিম 017xxxxxxxx`\n'
        '   `করিম 018xxxxxxxx`\n'
        '২. 📖 VCF ফাইল থেকে তথ্য পড়তে: একটি .vcf ফাইল আপলোড করুন।\n\n'
        'আপনি https://contactum.vercel.app/ ওয়েবপেজ থেকেও এই সার্ভিস ব্যবহার করতে পারবেন!'
    )

async def handle_message(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    if text:
        vcf_content = process_text_to_vcf_bulk(text)
        if vcf_content.strip():
            # Create a BytesIO object to simulate a file
            vcf_file = BytesIO(vcf_content.encode('utf-8'))
            vcf_file.name = 'contacts.vcf' # Give it a filename for Telegram

            await update.message.reply_document(
                document=vcf_file,
                filename='contacts.vcf',
                caption='আপনার কন্টাক্ট VCF ফাইলটি তৈরি হয়ে গেছে!'
            )
        else:
            await update.message.reply_text("কোনো বৈধ কন্টাক্ট পাওয়া যায়নি। অনুগ্রহ করে সঠিক ফরম্যাটে নাম ও নম্বর দিন।")

async def handle_document(update: Update, context: CallbackContext) -> None:
    if update.message.document and update.message.document.file_name.endswith('.vcf'):
        file_id = update.message.document.file_id
        file = await context.bot.get_file(file_id)
        file_content = await file.download_as_bytearray()
        
        vcf_text = file_content.decode('utf-8')
        contacts = parse_vcf_string(vcf_text)

        if contacts:
            response_text = "আপনার VCF ফাইলের কন্টাক্টগুলি:\n"
            for contact in contacts:
                response_text += f"নাম: {contact.get('name', 'N/A')}, ফোন: {contact.get('phone', 'N/A')}\n"
            await update.message.reply_text(response_text)
        else:
            await update.message.reply_text("VCF ফাইল থেকে কোনো কন্টাক্ট পড়া যায়নি।")
    else:
        await update.message.reply_text("অনুগ্রহ করে একটি .vcf ফাইল আপলোড করুন।")


# --- Vercel Serverless Function Entry Point ---
# This class acts as a simple HTTP server to handle Vercel's requests
class TelegramWebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # Use Updater to process the update
        # For Vercel, we receive one update at a time via webhook
        # We need to manually create an Update object and pass it
        update_json = json.loads(post_data)
        
        # Manually create an Update object (this is a simplified approach, 
        # for a full Updater you might need more setup)
        # For simplicity and Vercel's single-request model, we'll process directly.
        # This requires `python-telegram-bot` to handle update parsing.

        try:
            update = Update.de_json(update_json, bot)
            
            # This is a simplified way to route. In a full `Updater` setup, 
            # handlers are registered and dispatched automatically.
            # For serverless, we check message types manually.
            
            if update.message:
                if update.message.text == '/start':
                    context = CallbackContext(dispatcher=None, user_data={}, chat_data={}) # Dummy context
                    asyncio.run(start(update, context))
                elif update.message.document:
                    context = CallbackContext(dispatcher=None, user_data={}, chat_data={})
                    asyncio.run(handle_document(update, context))
                elif update.message.text:
                    context = CallbackContext(dispatcher=None, user_data={}, chat_data={})
                    asyncio.run(handle_message(update, context))
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')

        except Exception as e:
            print(f"Error processing update: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f'Error: {e}'.encode('utf-8'))

    def do_GET(self):
        # A simple GET request for the root path might indicate the bot is alive or for webhook setup
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<h1>Contactum Bot is Running!</h1><p>Set your Telegram webhook to this URL.</p>')

# Vercel handler for Python is usually a function, not a class
# We'll use a simple wrapper to make it compatible
async def handler(request):
    # This is a placeholder for `vercel.json` if you're directly mapping `api/index.py`
    # For a full Telegram Bot webhook, the POST request body is the Update object.
    # The `TelegramWebhookHandler` class above is for a more generic HTTP server.
    # For Vercel, we receive the request object directly.

    if request.method == 'POST':
        try:
            # Read the request body
            body = await request.json() # Vercel's request object might have .json() method

            update = Update.de_json(body, bot)
            
            # Dispatch based on message type
            if update.message:
                context = CallbackContext(dispatcher=None, user_data={}, chat_data={}) # Simplified context
                if update.message.text == '/start':
                    await start(update, context)
                elif update.message.document:
                    await handle_document(update, context)
                elif update.message.text:
                    await handle_message(update, context)
            
            return {'statusCode': 200, 'body': 'OK'}
        except Exception as e:
            print(f"Error processing update: {e}")
            return {'statusCode': 500, 'body': f'Error: {e}'}
    
    elif request.method == 'GET':
        return {'statusCode': 200, 'headers': {'Content-type': 'text/html'}, 'body': '<h1>Contactum Bot is Running!</h1><p>Set your Telegram webhook to this URL.</p>'}


# To make `python-telegram-bot` work with Vercel's serverless function, 
# you'll typically interact with the `Update` object directly from the webhook payload.
# The `Updater` class is designed for long-running processes, not serverless.

# Instead of `Updater`, you'd directly process the `update_json`.
# For Vercel, `api/index.py` needs to export a callable (function or class instance)
# that Vercel invokes. The `handler` function is a better fit for Vercel.

# We'll use the `handler` function directly for Vercel.
# The `TelegramWebhookHandler` class is more for local testing with `HTTPServer`.
import asyncio
if BOT_TOKEN:
    # Set the webhook when the script is deployed and accessed for the first time
    # This might run during Vercel build process, so ensure it doesn't fail.
    # Best practice is to set webhook via a separate script or command once deployed.
    # await bot.set_webhook(url=f"https://contactum.vercel.app/api") # This needs to be async and called once.
    pass # We will set webhook manually or via `vercel.json` rewrite
