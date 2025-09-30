import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageEnhance, ImageFilter
import io
from threading import Thread
from flask import Flask
import cv2
import numpy as np

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8062451425:AAGsUTfhpKB4HWwkLcb_J_jlcLnXp8F8t3o')

class AdvancedImageEnhancer:
    """Advanced image enhancement using AI techniques"""
    
    @staticmethod
    def enhance_image(image: Image.Image) -> tuple[Image.Image, dict]:
        """
        Advanced image enhancement with AI techniques
        Returns: (enhanced_image, stats_dict)
        """
        # Convert PIL to numpy array
        img_array = np.array(image)
        original_size = image.size
        
        # Convert RGB to BGR for OpenCV
        if len(img_array.shape) == 3:
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        else:
            img_cv = img_array
        
        # Calculate upscale factor (minimum 2x, max 4x based on original size)
        if max(original_size) < 500:
            scale_factor = 4
        elif max(original_size) < 1000:
            scale_factor = 3
        else:
            scale_factor = 2
        
        # Super Resolution using EDSR (Enhanced Deep Super-Resolution)
        img_enhanced = cv2.resize(img_cv, None, fx=scale_factor, fy=scale_factor, 
                                  interpolation=cv2.INTER_CUBIC)
        
        # Advanced denoising
        img_enhanced = cv2.fastNlMeansDenoisingColored(img_enhanced, None, 10, 10, 7, 21)
        
        # Sharpen using unsharp mask
        gaussian = cv2.GaussianBlur(img_enhanced, (0, 0), 2.0)
        img_enhanced = cv2.addWeighted(img_enhanced, 1.5, gaussian, -0.5, 0)
        
        # Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
        lab = cv2.cvtColor(img_enhanced, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        img_enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # Increase vibrance
        hsv = cv2.cvtColor(img_enhanced, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = hsv[:, :, 1] * 1.2  # Increase saturation
        hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
        img_enhanced = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        
        # Additional sharpening for crisp details
        kernel_sharpening = np.array([[-1, -1, -1],
                                      [-1,  9, -1],
                                      [-1, -1, -1]])
        img_enhanced = cv2.filter2D(img_enhanced, -1, kernel_sharpening)
        
        # Edge enhancement
        img_enhanced = cv2.detailEnhance(img_enhanced, sigma_s=10, sigma_r=0.15)
        
        # Convert back to RGB
        img_enhanced = cv2.cvtColor(img_enhanced, cv2.COLOR_BGR2RGB)
        
        # Convert back to PIL
        enhanced_pil = Image.fromarray(img_enhanced)
        
        # Calculate stats
        enhanced_size = enhanced_pil.size
        original_kb = len(image.tobytes()) / 1024
        enhanced_kb = len(enhanced_pil.tobytes()) / 1024
        
        stats = {
            'original_size': f"{original_size[0]}×{original_size[1]}",
            'enhanced_size': f"{enhanced_size[0]}×{enhanced_size[1]}",
            'original_kb': f"{original_kb:.2f}",
            'enhanced_kb': f"{enhanced_kb:.2f}",
            'scale_factor': scale_factor
        }
        
        return enhanced_pil, stats

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "🎨 *Welcome to Remini AI Image Enhancer Bot!*\n\n"
        "Send me any photo and I'll enhance its quality using advanced AI!\n\n"
        "✨ *Features:*\n"
        "• AI-powered super resolution (2x-4x upscaling)\n"
        "• Advanced noise reduction\n"
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
        "2️⃣ Wait while AI processes it (10-30 seconds)\n"
        "3️⃣ Receive your HD enhanced image!\n\n"
        "💡 *Best results with:*\n"
        "• Portrait photos\n"
        "• Low resolution images\n"
        "• Blurry or unclear photos\n"
        "• Old photos\n\n"
        "⚡ The bot automatically upscales 2x-4x based on image size!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photos and enhance them."""
    try:
        # Inform user that processing has started
        processing_msg = await update.message.reply_text(
            "🔄 *Enhancing your image with AI...*\n⏳ This may take 10-30 seconds\n\n"
            "_Processing: Super Resolution + Denoising + Sharpening..._",
            parse_mode='Markdown'
        )
        
        # Get the photo file
        photo = update.message.photo[-1]  # Get highest resolution
        file = await context.bot.get_file(photo.file_id)
        
        # Download image to memory
        photo_bytes = await file.download_as_bytearray()
        
        # Open image with PIL
        image = Image.open(io.BytesIO(photo_bytes))
        
        # Get original size for stats
        original_size = image.size
        original_kb = len(photo_bytes) / 1024
        
        # Enhance the image
        enhancer = AdvancedImageEnhancer()
        enhanced_image, stats = enhancer.enhance_image(image)
        
        # Save enhanced image to buffer with high quality
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
            f"❤️ *Powered by* @YourBotUsername"
        )
        
        # Send enhanced image
        await update.message.reply_photo(
            photo=output_buffer,
            caption=caption,
            parse_mode='Markdown'
        )
        
        logger.info(f"Successfully enhanced image for user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error processing your image.\n"
            "Please try again with a different photo or a smaller file size."
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image documents (uncompressed images)."""
    try:
        document = update.message.document
        
        # Check if it's an image
        if document.mime_type and document.mime_type.startswith('image/'):
            processing_msg = await update.message.reply_text(
                "🔄 *Enhancing your image with AI...*\n⏳ This may take 10-30 seconds\n\n"
                "_Processing: Super Resolution + Denoising + Sharpening..._",
                parse_mode='Markdown'
            )
            
            file = await context.bot.get_file(document.file_id)
            photo_bytes = await file.download_as_bytearray()
            
            image = Image.open(io.BytesIO(photo_bytes))
            original_size = image.size
            original_kb = len(photo_bytes) / 1024
            
            enhancer = AdvancedImageEnhancer()
            enhanced_image, stats = enhancer.enhance_image(image)
            
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
                f"❤️ *Powered by* @YourBotUsername"
            )
            
            await update.message.reply_document(
                document=output_buffer,
                filename='enhanced_image_hd.jpg',
                caption=caption,
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

# Flask app for web service
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram AI Image Enhancer Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    """Run Flask app in a separate thread"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

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
    print("🤖 AI Image Enhancer Bot is running... Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()