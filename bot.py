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

class OptimizedImageEnhancer:
    """Memory-optimized image enhancement"""
    
    @staticmethod
    def enhance_image(image: Image.Image) -> tuple[Image.Image, dict]:
        """
        Optimized image enhancement with memory management
        """
        # Store original stats
        original_size = image.size
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Determine scale factor based on image size
        max_dimension = max(original_size)
        if max_dimension < 400:
            scale_factor = 3.5
        elif max_dimension < 800:
            scale_factor = 2.8
        else:
            scale_factor = 2.0
        
        # Calculate new size
        new_size = (int(original_size[0] * scale_factor), int(original_size[1] * scale_factor))
        
        # Upscale with Lanczos (high quality)
        image = image.resize(new_size, Image.LANCZOS)
        
        # Apply aggressive sharpening
        image = image.filter(ImageFilter.UnsharpMask(radius=2.5, percent=180, threshold=2))
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        # Apply detail filter
        image = image.filter(ImageFilter.DETAIL)
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.3)
        
        # Enhance color
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.15)
        
        # Enhance brightness slightly
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.05)
        
        # Second pass sharpening for extra clarity
        image = image.filter(ImageFilter.SHARPEN)
        image = image.filter(ImageFilter.SHARPEN)
        
        # Edge enhance
        image = image.filter(ImageFilter.EDGE_ENHANCE_MORE)
        
        # Final unsharp mask
        image = image.filter(ImageFilter.UnsharpMask(radius=1.5, percent=150, threshold=1))
        
        # Limit final size to prevent memory issues
        max_final_size = 3000
        if max(image.size) > max_final_size:
            ratio = max_final_size / max(image.size)
            final_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            image = image.resize(final_size, Image.LANCZOS)
        
        # Force garbage collection
        gc.collect()
        
        # Calculate stats
        enhanced_size = image.size
        
        stats = {
            'original_size': f"{original_size[0]}×{original_size[1]}",
            'enhanced_size': f"{enhanced_size[0]}×{enhanced_size[1]}",
            'scale_factor': scale_factor
        }
        
        return image, stats

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "🎨 *Welcome to Remini AI Image Enhancer Bot!*\n\n"
        "Send me any photo and I'll enhance its quality!\n\n"
        "✨ *Features:*\n"
        "• AI-powered enhancement\n"
        "• 2x-3.5x super resolution\n"
        "• Professional sharpness & clarity\n"
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
        "2️⃣ Wait a few seconds while I enhance it\n"
        "3️⃣ Receive your HD enhanced image!\n\n"
        "💡 *Tips:*\n"
        "• Works best with photos of people, landscapes\n"
        "• Automatically upscales 2x-3.5x\n"
        "• Original aspect ratio preserved\n\n"
        "⚡ Send a photo now to try it out!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photos and enhance them."""
    try:
        # Inform user that processing has started
        processing_msg = await update.message.reply_text(
            "🔄 Enhancing your image...\n⏳ Please wait a moment"
        )
        
        # Get the photo file
        photo = update.message.photo[-1]  # Get highest resolution
        file = await context.bot.get_file(photo.file_id)
        
        # Download image to memory
        photo_bytes = await file.download_as_bytearray()
        original_kb = len(photo_bytes) / 1024
        
        # Open image with PIL
        image = Image.open(io.BytesIO(photo_bytes))
        original_size = image.size
        
        # Clear memory
        del photo_bytes
        gc.collect()
        
        # Enhance the image
        enhancer = OptimizedImageEnhancer()
        enhanced_image, stats = enhancer.enhance_image(image)
        
        # Clear original image
        del image
        gc.collect()
        
        # Save enhanced image to buffer
        output_buffer = io.BytesIO()
        enhanced_image.save(output_buffer, format='JPEG', quality=95, optimize=True)
        enhanced_kb = output_buffer.tell() / 1024
        output_buffer.seek(0)
        
        # Delete processing message
        await processing_msg.delete()
        
        # Create caption with stats
        caption = (
            f"✅ *Image Enhanced!*\n\n"
            f"📦 *Original Size:* {stats['original_size']}  {original_kb:.2f} KB\n"
            f"📦 *Enhanced Size:* {stats['enhanced_size']}  {enhanced_kb:.2f} KB\n"
            f"🎬 *Quality:* Enhanced (HD)\n\n"
            f"❤️ *Powered by* @Dailynewswalla"
        )
        
        # Send enhanced image
        await update.message.reply_photo(
            photo=output_buffer,
            caption=caption,
            parse_mode='Markdown'
        )
        
        # Clear memory
        del enhanced_image
        del output_buffer
        gc.collect()
        
        logger.info(f"Successfully enhanced image for user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error processing your image.\n"
            "Please try again with a smaller photo."
        )
        gc.collect()

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image documents (uncompressed images)."""
    try:
        document = update.message.document
        
        # Check if it's an image
        if document.mime_type and document.mime_type.startswith('image/'):
            # Check file size (limit to 5MB to prevent memory issues)
            if document.file_size > 5 * 1024 * 1024:
                await update.message.reply_text(
                    "⚠️ File too large. Please send images smaller than 5MB."
                )
                return
            
            processing_msg = await update.message.reply_text(
                "🔄 Enhancing your image...\n⏳ Please wait a moment"
            )
            
            file = await context.bot.get_file(document.file_id)
            photo_bytes = await file.download_as_bytearray()
            original_kb = len(photo_bytes) / 1024
            
            image = Image.open(io.BytesIO(photo_bytes))
            original_size = image.size
            
            del photo_bytes
            gc.collect()
            
            enhancer = OptimizedImageEnhancer()
            enhanced_image, stats = enhancer.enhance_image(image)
            
            del image
            gc.collect()
            
            output_buffer = io.BytesIO()
            enhanced_image.save(output_buffer, format='JPEG', quality=95, optimize=True)
            enhanced_kb = output_buffer.tell() / 1024
            output_buffer.seek(0)
            
            await processing_msg.delete()
            
            caption = (
                f"✅ *Image Enhanced!*\n\n"
                f"📦 *Original Size:* {stats['original_size']}  {original_kb:.2f} KB\n"
                f"📦 *Enhanced Size:* {stats['enhanced_size']}  {enhanced_kb:.2f} KB\n"
                f"🎬 *Quality:* Enhanced (HD)\n\n"
                f"❤️ *Powered by* @Dailynewswalla"
            )
            
            await update.message.reply_document(
                document=output_buffer,
                filename='enhanced_image_hd.jpg',
                caption=caption,
                parse_mode='Markdown'
            )
            
            del enhanced_image
            del output_buffer
            gc.collect()
            
            logger.info(f"Successfully enhanced document image for user {update.effective_user.id}")
        else:
            await update.message.reply_text(
                "⚠️ Please send an image file (JPG, PNG, etc.)"
            )
            
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error processing your image.\n"
            "Please try again with a different photo."
        )
        gc.collect()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")

# Flask app for web service
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Image Enhancer Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    """Run Flask app in a separate thread"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)

def main():
    """Start the bot."""
    # Start Flask in background thread
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
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Bot started successfully!")
    print("🤖 Image Enhancer Bot is running... Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()