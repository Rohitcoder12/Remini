import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageEnhance, ImageFilter
import io
from threading import Thread
from flask import Flask
import gc

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8062451425:AAGsUTfhpKB4HWwkLcb_J_jlcLnXp8F8t3o')

class ImageEnhancer:
    """Optimized image enhancement"""
    
    @staticmethod
    def enhance_image(image: Image.Image) -> tuple[Image.Image, dict]:
        """
        Enhanced image processing with quality focus
        """
        try:
            # Store original stats
            original_size = image.size
            
            # Convert to RGB if necessary (handle transparency)
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Calculate intelligent scale factor
            max_dim = max(original_size)
            if max_dim < 500:
                scale = 3.0
            elif max_dim < 1000:
                scale = 2.5
            else:
                scale = 2.0
            
            # Calculate new dimensions
            new_width = int(original_size[0] * scale)
            new_height = int(original_size[1] * scale)
            
            # Limit to prevent memory issues (max 2500px)
            max_size = 2500
            if max(new_width, new_height) > max_size:
                ratio = max_size / max(new_width, new_height)
                new_width = int(new_width * ratio)
                new_height = int(new_height * ratio)
            
            new_size = (new_width, new_height)
            
            # High-quality upscaling
            image = image.resize(new_size, Image.LANCZOS)
            
            # Step 1: Noise reduction (slight blur then sharpen)
            image = image.filter(ImageFilter.GaussianBlur(0.5))
            
            # Step 2: Aggressive sharpening
            image = image.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
            
            # Step 3: Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.8)
            
            # Step 4: Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            
            # Step 5: Color enhancement
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.1)
            
            # Step 6: Brightness
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.03)
            
            # Step 7: Detail enhancement
            image = image.filter(ImageFilter.DETAIL)
            
            # Step 8: Final sharpening
            image = image.filter(ImageFilter.SHARPEN)
            
            # Step 9: Edge enhancement
            image = image.filter(ImageFilter.EDGE_ENHANCE)
            
            # Calculate stats
            enhanced_size = image.size
            
            stats = {
                'original_size': f"{original_size[0]}×{original_size[1]}",
                'enhanced_size': f"{enhanced_size[0]}×{enhanced_size[1]}",
                'scale_factor': scale
            }
            
            return image, stats
            
        except Exception as e:
            logger.error(f"Enhancement error: {e}")
            raise

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "🎨 *Welcome to Remini AI Image Enhancer Bot!*\n\n"
        "Send me any photo and I'll enhance its quality!\n\n"
        "✨ *Features:*\n"
        "• 2x-3x super resolution\n"
        "• Professional sharpness\n"
        "• Enhanced colors & contrast\n"
        "• Detail preservation\n\n"
        "📸 Just send me a photo to get started!"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "📖 *How to use:*\n\n"
        "1️⃣ Send me any photo\n"
        "2️⃣ Wait a few seconds\n"
        "3️⃣ Get your HD enhanced image!\n\n"
        "💡 *Tips:*\n"
        "• Send compressed photos (not as document)\n"
        "• Works best with portraits\n"
        "• Automatic quality optimization\n\n"
        "⚡ Try it now!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photos and enhance them."""
    processing_msg = None
    try:
        # Inform user that processing has started
        processing_msg = await update.message.reply_text(
            "🔄 *Enhancing your image...*\n⏳ Please wait",
            parse_mode='Markdown'
        )
        
        # Get the photo file
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Download image
        photo_bytes = await file.download_as_bytearray()
        original_kb = len(photo_bytes) / 1024
        
        # Open image
        image = Image.open(io.BytesIO(photo_bytes))
        original_size = image.size
        
        logger.info(f"Processing image: {original_size[0]}x{original_size[1]}, {original_kb:.2f}KB")
        
        # Free memory
        del photo_bytes
        gc.collect()
        
        # Enhance the image
        enhancer = ImageEnhancer()
        enhanced_image, stats = enhancer.enhance_image(image)
        
        logger.info(f"Enhanced to: {enhanced_image.size[0]}x{enhanced_image.size[1]}")
        
        # Clear original
        del image
        gc.collect()
        
        # Save with high quality
        output_buffer = io.BytesIO()
        enhanced_image.save(
            output_buffer, 
            format='JPEG', 
            quality=95,
            optimize=True,
            progressive=True
        )
        enhanced_kb = output_buffer.tell() / 1024
        output_buffer.seek(0)
        
        # Delete processing message
        if processing_msg:
            await processing_msg.delete()
        
        # Create caption
        caption = (
            f"✅ *Image Enhanced!*\n\n"
            f"📦 *Original Size:* {stats['original_size']}  {original_kb:.2f} KB\n"
            f"📦 *Enhanced Size:* {stats['enhanced_size']}  {enhanced_kb:.2f} KB\n"
            f"🎬 *Quality:* Enhanced (HD)\n\n"
            f"❤️ *Powered by* @YourBotUsername"
        )
        
        # Send enhanced image
        await update.message.reply_photo(
            photo=output_buffer,
            caption=caption,
            parse_mode='Markdown'
        )
        
        # Cleanup
        del enhanced_image
        del output_buffer
        gc.collect()
        
        logger.info(f"Successfully enhanced image for user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}", exc_info=True)
        
        error_msg = (
            "❌ *Enhancement failed*\n\n"
            "Possible reasons:\n"
            "• Image too large\n"
            "• Corrupted file\n"
            "• Server memory limit\n\n"
            "Try:\n"
            "• Smaller image\n"
            "• Different format\n"
            "• Compressed photo"
        )
        
        if processing_msg:
            await processing_msg.edit_text(error_msg, parse_mode='Markdown')
        else:
            await update.message.reply_text(error_msg, parse_mode='Markdown')
        
        # Force cleanup
        gc.collect()

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image documents."""
    try:
        document = update.message.document
        
        # Check if it's an image
        if not (document.mime_type and document.mime_type.startswith('image/')):
            await update.message.reply_text(
                "⚠️ Please send an image file (JPG, PNG, etc.)"
            )
            return
        
        # Check file size (max 3MB for documents)
        if document.file_size > 3 * 1024 * 1024:
            await update.message.reply_text(
                "⚠️ File too large. Please send images under 3MB.\n"
                "Tip: Send as a photo (compressed) instead of document."
            )
            return
        
        processing_msg = await update.message.reply_text(
            "🔄 *Enhancing your image...*\n⏳ Please wait",
            parse_mode='Markdown'
        )
        
        file = await context.bot.get_file(document.file_id)
        photo_bytes = await file.download_as_bytearray()
        original_kb = len(photo_bytes) / 1024
        
        image = Image.open(io.BytesIO(photo_bytes))
        
        del photo_bytes
        gc.collect()
        
        enhancer = ImageEnhancer()
        enhanced_image, stats = enhancer.enhance_image(image)
        
        del image
        gc.collect()
        
        output_buffer = io.BytesIO()
        enhanced_image.save(
            output_buffer,
            format='JPEG',
            quality=95,
            optimize=True,
            progressive=True
        )
        enhanced_kb = output_buffer.tell() / 1024
        output_buffer.seek(0)
        
        await processing_msg.delete()
        
        caption = (
            f"✅ *Image Enhanced!*\n\n"
            f"📦 *Original Size:* {stats['original_size']}  {original_kb:.2f} KB\n"
            f"📦 *Enhanced Size:* {stats['enhanced_size']}  {enhanced_kb:.2f} KB\n"
            f"🎬 *Quality:* Enhanced (HD)\n\n"
            f"❤️ *Powered by* @YourBotUsername"
        )
        
        await update.message.reply_document(
            document=output_buffer,
            filename='enhanced_hd.jpg',
            caption=caption,
            parse_mode='Markdown'
        )
        
        del enhanced_image
        del output_buffer
        gc.collect()
        
        logger.info(f"Successfully enhanced document for user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "❌ *Enhancement failed*\n"
            "Please try sending as a regular photo instead.",
            parse_mode='Markdown'
        )
        gc.collect()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)

# Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Image Enhancer Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    """Run Flask server"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)

def main():
    """Start the bot"""
    # Start Flask
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Bot started successfully!")
    print("🤖 Image Enhancer Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()