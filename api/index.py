import os
import re
from io import BytesIO
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import json
import asyncio # For running async functions in a synchronous context (Vercel handler)

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
        line = line.strip() # Clean extra whitespace
        if not line: continue

        if line.startswith("BEGIN:VCARD"):
            current_contact = {}
        elif line.startswith("N:"):
            # N:LastName;FirstName;MiddleName;Prefix;Suffix
            parts = line[2:].split(';')
            first_name = parts[1] if len(parts) > 1 else ""
            last_name = parts[0] if len(parts) > 0 else ""
            current_contact['name'] = f"{first_name} {last_name}".strip()
        elif line.startswith("TEL;"):
            # TEL;TYPE=CELL;VALUE=VOICE:+88017xxxxxxxx or TEL:+88017xxxxxxxx
            # Extract number, trying to get digits after ':' or directly
            match = re.search(r'(?:\+?\d+)', line) # Find any sequence of digits, potentially with '+'
            if match:
                phone_number = re.sub(r'\D', '', match.group(0)) # Clean non-digits
                if phone_number:
                    current_contact['phone'] = format_number(phone_number) # Reformat for consistency
        elif line.startswith("END:VCARD"):
            if 'name' in current_contact and 'phone' in current_contact:
                contacts.append(current_contact)
            current_contact = {} # Reset for next contact
    return contacts

# --- Telegram Bot Handlers ---
# !! WARNING: Hardcoding bot token is not recommended for production environments.
# !! For a real project, always use environment variables.
BOT_TOKEN = "8523158193:AAE7LKktxM-vq13I1aoHqyID6BTdfTJUnv8"

bot = Bot(token=BOT_TOKEN)

async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    bot_info = await context.bot.get_me()
    
    await update.message.reply_text(
        f'নমস্কার, {user.full_name} ({user.id})! 👋\n'
        f'আমি {bot_info.first_name} বট, আপনাকে স্বাগতম!\n\n'
        'আমার কার্যকারিতা সম্পর্কে জানতে `/help` কমান্ডটি ব্যবহার করুন।'
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'আমি আপনার টেক্সট থেকে VCF ফাইল তৈরি করতে অথবা VCF ফাইল থেকে কন্টাক্ট ইনফো এক্সট্রাক্ট করতে সাহায্য করব।\n\n'
        'ব্যবহারবিধি:\n'
        '১. 📞 কন্টাক্ট তৈরি করতে: নাম এবং নম্বর লিখুন (প্রতি লাইনে একটি করে)।\n'
        '   যেমন:\n'
        '   `রহিম 017xxxxxxxx`\n'
        '   `করিম 018xxxxxxxx`\n'
        '   আপনি বাল্ক লিস্টও পেস্ট করতে পারেন।\n'
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
            await update.message.reply_text("কোনো বৈধ কন্টাক্ট পাওয়া যায়নি। অনুগ্রহ করে সঠিক ফরম্যাটে নাম ও নম্বর দিন অথবা `/help` ব্যবহার করুন।")

async def handle_document(update: Update, context: CallbackContext) -> None:
    if update.message.document and update.message.document.file_name.lower().endswith('.vcf'):
        file_id = update.message.document.file_id
        file = await context.bot.get_file(file_id)
        
        # Download file content
        file_content_bytes = BytesIO()
        await file.download_to_memory(file_content_bytes)
        file_content_bytes.seek(0) # Reset stream position to beginning

        vcf_text = file_content_bytes.read().decode('utf-8')
        contacts = parse_vcf_string(vcf_text)

        if contacts:
            response_text = "আপনার VCF ফাইলের কন্টাক্টগুলি:\n"
            for i, contact in enumerate(contacts):
                response_text += f"{i+1}. নাম: {contact.get('name', 'N/A')}, ফোন: {contact.get('phone', 'N/A')}\n"
            
            # Telegram message limit is 4096 characters. Split if too long.
            if len(response_text) > 4000:
                await update.message.reply_text("কন্টাক্ট লিস্ট অনেক লম্বা, প্রথম কিছু কন্টাক্ট দেখানো হলো:")
                await update.message.reply_text(response_text[:4000] + "...")
            else:
                await update.message.reply_text(response_text)
        else:
            await update.message.reply_text("VCF ফাইল থেকে কোনো কন্টাক্ট পড়া যায়নি। ফাইলটি ঠিক আছে কিনা নিশ্চিত করুন।")
    else:
        await update.message.reply_text("অনুগ্রহ করে একটি .vcf ফাইল আপলোড করুন।")


# --- Vercel Serverless Function Entry Point ---
# This function will be called by Vercel when a request comes to /api
async def handler(request):
    if request.method == 'POST':
        try:
            # Vercel's request object can directly provide JSON body
            body = await request.json() 

            update = Update.de_json(body, bot)
            
            # We need a dummy context as we are not using Updater
            context = CallbackContext(dispatcher=None, user_data={}, chat_data={}) 

            if update.message:
                if update.message.text == '/start':
                    await start(update, context)
                elif update.message.text == '/help':
                    await help_command(update, context)
                elif update.message.document:
                    await handle_document(update, context)
                elif update.message.text: # General text message handler
                    await handle_message(update, context)
            
            return {'statusCode': 200, 'body': 'OK'}
        except Exception as e:
            print(f"Error processing update: {e}")
            return {'statusCode': 500, 'body': f'Error: {e}'}
    
    elif request.method == 'GET':
        # Simple GET request to indicate the bot is alive and provide webhook setup info
        return {
            'statusCode': 200, 
            'headers': {'Content-type': 'text/html'}, 
            'body': '<h1>Contactum Bot is Running!</h1><p>Set your Telegram webhook to this URL: <code>https://contactum.vercel.app/api</code> (replace with your Vercel domain).</p>'
        }
    
    return {'statusCode': 405, 'body': 'Method Not Allowed'} # For other HTTP methods
