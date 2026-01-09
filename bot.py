import logging
import io
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler

# আপনার টোকেন
TOKEN = "8523158193:AAE7LKktxM-vq13I1aoHqyID6BTdfTJUnv8"

# কন্টাক্ট ফরম্যাটিং লজিক
def format_number(num_str):
    bengali_digits = "০১২৩৪৫৬৭৮৯"
    english_digits = "0123456789"
    for b, e in zip(bengali_digits, english_digits):
        num_str = num_str.replace(b, e)
    clean_num = re.sub(r'\D', '', num_str)
    if clean_num.startswith('880'): clean_num = clean_num[2:]
    if clean_num.startswith('0'): return f"+88{clean_num}"
    return f"+880{clean_num}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("স্বাগতম! আমাকে নাম ও নম্বর পাঠান কন্টাক্ট ফাইল তৈরি করতে, অথবা একটি .vcf ফাইল পাঠান সেটি রিড করতে।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lines = text.strip().split('\n')
    vcf_content = ""
    
    for line in lines:
        clean_line = re.sub(r'[•°:>]', ' ', line).strip()
        phones = re.findall(r'(?:\+?88)?01[3-9]\d{8}', clean_line)
        if phones:
            phone = phones[0]
            name = clean_line.replace(phone, '').strip() or "No Name"
            vcf_content += f"BEGIN:VCARD\nVERSION:2.1\nN:{name};;;\nTEL;CELL;PREF:{format_number(phone)}\nEND:VCARD\n"
    
    if vcf_content:
        bio = io.BytesIO(vcf_content.encode())
        bio.name = "contacts.vcf"
        await update.message.reply_document(document=bio, caption="আপনার কন্টাক্ট ফাইল তৈরি হয়েছে।")
    else:
        await update.message.reply_text("সঠিক কোনো নম্বর খুঁজে পাওয়া যায়নি।")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document.file_name.endswith('.vcf'):
        file = await context.bot.get_file(update.message.document.file_id)
        content = await file.download_as_bytearray()
        decoded_content = content.decode('utf-8', errors='ignore')
        
        # রিভার্স রিডিং লজিক
        names = re.findall(r'N:(.*?);;;', decoded_content)
        phones = re.findall(r'TEL;.*?[:](.*?)\n', decoded_content)
        
        result = "📄 কন্টাক্ট লিস্ট বিবরণ:\n\n"
        for n, p in zip(names, phones):
            result += f"👤 {n.strip()} 📞 {p.strip()}\n"
        
        await update.message.reply_text(result if len(names) > 0 else "ফাইলের ভেতর কোনো কন্টাক্ট পাওয়া যায়নি।")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.Document.MimeType("text/vcard") | filters.Document.FileExtension("vcf"), handle_document))
    
    print("Bot is running...")
    app.run_polling()
