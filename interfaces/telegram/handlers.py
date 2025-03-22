async def handle_button(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("explain_"):
        file_path = query.data.split("_", 1)[1]
        explanation = get_code_explanation(file_path)
        await query.edit_message_text(explanation)
    
    elif query.data == "status":
        status = get_system_status()
        await query.edit_message_text(status)

async def handle_message(update: Update, context):
    if update.message.document:
        await process_uploaded_file(update)
    else:
        await handle_freeform_query(update)

async def process_uploaded_file(update: Update):
    file = await update.message.document.get_file()
    await file.download_to_drive()
    await update.message.reply_text("📁 File received. Analyzing...")
    
async def handle_recommend(update: Update, context):
    advisor = CodeAdvisor()
    recommendations = advisor.generate_recommendations()
    
    response = "🔍 Code Recommendations:\n"
    response += "\n🏛 Architectural:\n- " + "\n- ".join(recommendations['architectural'][:3])
    response += "\n🔐 Security:\n- " + "\n- ".join(recommendations['security'][:3])
    
    await update.message.reply_markdown(response)