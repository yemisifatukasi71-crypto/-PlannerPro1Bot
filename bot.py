import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from database import Database

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from environment variables
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    raise ValueError("No TELEGRAM_TOKEN found in environment variables")

# Initialize database
db = Database()

# User session states
WAITING_FOR_TASK = 1
WAITING_FOR_DATE = 2
WAITING_FOR_CATEGORY = 3

# Category colors for display
CATEGORY_COLORS = {
    "Work": "🔵",
    "Personal": "🟢",
    "Urgent": "🔴",
    "Study": "📚",
    "Health": "💪",
    "Other": "📌"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Welcome {user.first_name} to PlannerPro Bot!\n\n"
        f"I'm your personal task manager. Here's what I can do:\n\n"
        f"📝 /addtask - Add a new task\n"
        f"📋 /mytasks - View all your tasks\n"
        f"✅ /complete - Mark a task as complete\n"
        f"🗑️ /delete - Delete a task\n"
        f"📅 /today - View today's tasks\n"
        f"📊 /stats - View your task statistics\n"
        f"❓ /help - Show this message again\n\n"
        f"Let's get organized! 🚀"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message."""
    await update.message.reply_text(
        "📋 **PlannerPro Commands**\n\n"
        "/start - Start the bot\n"
        "/addtask - Add a new task\n"
        "/mytasks - View all your tasks\n"
        "/complete - Mark a task as complete\n"
        "/delete - Delete a task\n"
        "/today - View today's tasks\n"
        "/stats - View your task statistics\n"
        "/help - Show this help message\n\n"
        "💡 **Tip**: Use /addtask to start adding tasks interactively!",
        parse_mode='Markdown'
    )

async def addtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the process of adding a new task."""
    user_id = update.effective_user.id
    context.user_data['state'] = WAITING_FOR_TASK
    
    await update.message.reply_text(
        "📝 Please enter your task description:\n\n"
        "(Example: 'Complete project proposal' or 'Buy groceries')"
    )

async def handle_task_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the task description input."""
    if context.user_data.get('state') != WAITING_FOR_TASK:
        return
    
    task_description = update.message.text
    context.user_data['task_description'] = task_description
    context.user_data['state'] = WAITING_FOR_DATE
    
    # Create date selection keyboard
    keyboard = [
        [InlineKeyboardButton("Today", callback_data="date_today")],
        [InlineKeyboardButton("Tomorrow", callback_data="date_tomorrow")],
        [InlineKeyboardButton("Next 3 days", callback_data="date_3days")],
        [InlineKeyboardButton("Next Week", callback_data="date_week")],
        [InlineKeyboardButton("Custom Date (YYYY-MM-DD)", callback_data="date_custom")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📅 Task: '{task_description}'\n\n"
        f"When is this due? Choose an option:",
        reply_markup=reply_markup
    )

async def handle_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle date selection from inline keyboard."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    task_description = context.user_data.get('task_description')
    
    # Calculate due date based on selection
    today = datetime.now().date()
    if query.data == "date_today":
        due_date = today
    elif query.data == "date_tomorrow":
        due_date = today + timedelta(days=1)
    elif query.data == "date_3days":
        due_date = today + timedelta(days=3)
    elif query.data == "date_week":
        due_date = today + timedelta(days=7)
    elif query.data == "date_custom":
        context.user_data['state'] = WAITING_FOR_CATEGORY
        await query.edit_message_text(
            f"📝 Task: '{task_description}'\n\n"
            f"Please enter the custom date (YYYY-MM-DD):\n"
            f"Example: 2026-07-15"
        )
        return
    else:
        due_date = today + timedelta(days=1)
    
    context.user_data['due_date'] = due_date.strftime("%Y-%m-%d")
    context.user_data['state'] = WAITING_FOR_CATEGORY
    
    # Show category selection
    keyboard = [
        [InlineKeyboardButton("💼 Work", callback_data="cat_Work")],
        [InlineKeyboardButton("👤 Personal", callback_data="cat_Personal")],
        [InlineKeyboardButton("🔥 Urgent", callback_data="cat_Urgent")],
        [InlineKeyboardButton("📚 Study", callback_data="cat_Study")],
        [InlineKeyboardButton("💪 Health", callback_data="cat_Health")],
        [InlineKeyboardButton("📌 Other", callback_data="cat_Other")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 Task: '{task_description}'\n"
        f"📅 Due: {due_date.strftime('%Y-%m-%d')}\n\n"
        f"Select a category:",
        reply_markup=reply_markup
    )

async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection from inline keyboard."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    task_description = context.user_data.get('task_description')
    due_date = context.user_data.get('due_date')
    category = query.data.replace("cat_", "")
    
    # Save task to database
    try:
        db.add_task(user_id, task_description, due_date, category)
        
        await query.edit_message_text(
            f"✅ **Task added successfully!**\n\n"
            f"📝 Task: {task_description}\n"
            f"📅 Due: {due_date}\n"
            f"📊 Category: {CATEGORY_COLORS.get(category, '📌')} {category}\n\n"
            f"Keep up the great work! 🎯",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error saving task: {e}")
        await query.edit_message_text(
            "❌ Sorry, there was an error saving your task. Please try again."
        )
    
    # Clear user session
    context.user_data.clear()

async def mytasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all tasks for the user."""
    user_id = update.effective_user.id
    tasks = db.get_tasks(user_id)
    
    if not tasks:
        await update.message.reply_text(
            "📭 You have no tasks. Use /addtask to create one! 🚀"
        )
        return
    
    # Group tasks by status
    pending = [t for t in tasks if t['status'] == 'pending']
    completed = [t for t in tasks if t['status'] == 'completed']
    
    message = "📋 **Your Tasks**\n\n"
    
    if pending:
        message += "**📌 Pending Tasks:**\n"
        for i, task in enumerate(pending, 1):
            due_date = task['due_date'] or "No due date"
            category = CATEGORY_COLORS.get(task['category'], '📌')
            message += f"{i}. {category} {task['description']}\n"
            message += f"   📅 Due: {due_date}\n"
            message += f"   🆔 ID: `{task['id']}`\n\n"
    else:
        message += "✅ No pending tasks! Great job! 🎉\n\n"
    
    if completed:
        message += "**✅ Completed Tasks:**\n"
        for i, task in enumerate(completed[:5], 1):  # Show only last 5 completed
            message += f"{i}. ~~{task['description']}~~ ✅\n"
        if len(completed) > 5:
            message += f"... and {len(completed)-5} more completed tasks\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's tasks."""
    user_id = update.effective_user.id
    today_date = datetime.now().strftime("%Y-%m-%d")
    tasks = db.get_tasks_by_date(user_id, today_date)
    
    if not tasks:
        await update.message.reply_text(
            "📅 No tasks due today! Enjoy your day! 🌟"
        )
        return
    
    message = f"📅 **Tasks Due Today ({today_date})**\n\n"
    for i, task in enumerate(tasks, 1):
        category = CATEGORY_COLORS.get(task['category'], '📌')
        status = "✅" if task['status'] == 'completed' else "⏳"
        message += f"{i}. {status} {category} {task['description']}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark a task as complete."""
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        # Show pending tasks with numbers
        tasks = db.get_tasks(user_id, status='pending')
        if not tasks:
            await update.message.reply_text("✅ You have no pending tasks to complete!")
            return
        
        message = "✅ **Mark a task as complete**\n\n"
        message += "Use: /complete [task_id]\n\n"
        message += "Your pending tasks:\n"
        for task in tasks:
            message += f"🆔 `{task['id']}` - {task['description']}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    try:
        task_id = int(args[0])
        if db.complete_task(task_id, user_id):
            await update.message.reply_text(f"✅ Task #{task_id} marked as complete! Great job! 🎉")
        else:
            await update.message.reply_text("❌ Task not found or already completed.")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid task ID. Example: /complete 5")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a task."""
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        tasks = db.get_tasks(user_id)
        if not tasks:
            await update.message.reply_text("📭 You have no tasks to delete.")
            return
        
        message = "🗑️ **Delete a task**\n\n"
        message += "Use: /delete [task_id]\n\n"
        message += "Your tasks:\n"
        for task in tasks[:10]:  # Show first 10
            status = "✅" if task['status'] == 'completed' else "⏳"
            message += f"🆔 `{task['id']}` - {status} {task['description']}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    try:
        task_id = int(args[0])
        if db.delete_task(task_id, user_id):
            await update.message.reply_text(f"🗑️ Task #{task_id} has been deleted.")
        else:
            await update.message.reply_text("❌ Task not found.")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid task ID. Example: /delete 5")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show task statistics."""
    user_id = update.effective_user.id
    stats_data = db.get_stats(user_id)
    
    if stats_data['total'] == 0:
        await update.message.reply_text(
            "📊 You haven't created any tasks yet. Use /addtask to get started!"
        )
        return
    
    completion_rate = (stats_data['completed'] / stats_data['total'] * 100) if stats_data['total'] > 0 else 0
    
    message = f"📊 **Your Task Statistics**\n\n"
    message += f"📝 Total Tasks: {stats_data['total']}\n"
    message += f"⏳ Pending: {stats_data['pending']}\n"
    message += f"✅ Completed: {stats_data['completed']}\n"
    message += f"📈 Completion Rate: {completion_rate:.1f}%\n\n"
    
    message += "**Tasks by Category:**\n"
    for category, count in stats_data['by_category'].items():
        color = CATEGORY_COLORS.get(category, '📌')
        message += f"{color} {category}: {count}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addtask", addtask))
    application.add_handler(CommandHandler("mytasks", mytasks))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("complete", complete))
    application.add_handler(CommandHandler("delete", delete))
    application.add_handler(CommandHandler("stats", stats))
    
    # Message handler for task description
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_task_description
    ))
    
    # Callback handlers for inline keyboard
    application.add_handler(CallbackQueryHandler(handle_date_selection, pattern="^date_"))
    application.add_handler(CallbackQueryHandler(handle_category_selection, pattern="^cat_"))
    
    # Start the bot
    print("🤖 PlannerProBot is running!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
