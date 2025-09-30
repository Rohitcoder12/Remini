import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageEnhance, ImageFilter
import io

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Your bot token from BotFather
BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'

class ImageEnhancer:
    """Handles image enhancement operations"""
    
    @staticmethod
    def enhance_image(image: Image.Image) -> Image.Image:
        """
        Enhance image quality with multiple techniques
        """
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 1. Upscale image for better quality
        original_size = image.size
        scale_factor = 2
        new_size = (original_size[0] * scale_factor, original_size[1] * scale_factor)
        image = image.resize(new_size, Image.LANCZOS)
        
        # 2. Apply unsharp mask for sharpness
        image = image.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        
        # 3. Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.5)
        
        # 4. Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)
        
        # 5. Enhance color saturation
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.1)
        
        # 6. Enhance brightness slightly
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.05)
        
        # 7. Apply detail enhancement
        image = image.filter(ImageFilter.DETAIL)
        
        # Resize back to reasonable size (max 2048px on longest side)
        max_size = 2048
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            image = image.resize(new_size, Image.LANCZOS)
        
        return image

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "🎨 *Welcome to Remini AI Image Enhancer Bot!*\n\n"
        "Send me any photo and I'll enhance its quality!\n\n"
        "✨ *Features:*\n"
        "• AI-powered enhancement\n"
        "• Improved sharpness & clarity\n"
        "• Better colors & contrast\n"
        "• Upscaling support\n\n"
        "📸 Just send me a photo to get started!"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "📖 *How to use:*\n\n"
        "1️⃣ Send me any photo\n"
        "2️⃣ Wait a few seconds while I enhance it\n"
        "3️⃣ Receive your enhanced image!\n\n"
        "💡 *Tips:*\n"
        "• Works best with photos of people, landscapes, and objects\n"
        "• Original aspect ratio is preserved\n"
        "• Output is optimized for quality and file size\n\n"
        "⚡ Send a photo now to try it out!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photos and enhance them."""
    try:
        # Inform user that processing has started
        processing_msg = await update.message.reply_text(
            "🔄 Enhancing your image...\nPlease wait a moment ⏳"
        )
        
        # Get the photo file
        photo = update.message.photo[-1]  # Get highest resolution
        file = await context.bot.get_file(photo.file_id)
        
        # Download image to memory
        photo_bytes = await file.download_as_bytearray()
        
        # Open image with PIL
        image = Image.open(io.BytesIO(photo_bytes))
        
        # Enhance the image
        enhancer = ImageEnhancer()
        enhanced_image = enhancer.enhance_image(image)
        
        # Save enhanced image to buffer
        output_buffer = io.BytesIO()
        enhanced_image.save(output_buffer, format='JPEG', quality=95, optimize=True)
        output_buffer.seek(0)
        
        # Delete processing message
        await processing_msg.delete()
        
        # Send enhanced image
        await update.message.reply_photo(
            photo=output_buffer,
            caption="✅ *Image Enhanced!*\n\n🎨 Your photo has been processed with AI enhancement.",
            parse_mode='Markdown'
        )
        
        logger.info(f"Successfully enhanced image for user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error processing your image.\n"
            "Please try again with a different photo."
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image documents (in case user sends uncompressed)."""
    try:
        document = update.message.document
        
        # Check if it's an image
        if document.mime_type and document.mime_type.startswith('image/'):
            processing_msg = await update.message.reply_text(
                "🔄 Enhancing your image...\nPlease wait a moment ⏳"
            )
            
            file = await context.bot.get_file(document.file_id)
            photo_bytes = await file.download_as_bytearray()
            
            image = Image.open(io.BytesIO(photo_bytes))
            
            enhancer = ImageEnhancer()
            enhanced_image = enhancer.enhance_image(image)
            
            output_buffer = io.BytesIO()
            enhanced_image.save(output_buffer, format='JPEG', quality=95, optimize=True)
            output_buffer.seek(0)
            
            await processing_msg.delete()
            
            await update.message.reply_document(
                document=output_buffer,
                filename='enhanced_image.jpg',
                caption="✅ *Image Enhanced!*\n\n🎨 Your photo has been processed with AI enhancement.",
                parse_mode='Markdown'
            )
            
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

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot."""
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
    print("🤖 Bot is running... Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
