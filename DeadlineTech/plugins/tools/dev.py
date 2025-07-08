import os
import re
import subprocess
import sys
import traceback
from inspect import getfullargspec
from io import StringIO
from time import time

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from DeadlineTech import app
from config import OWNER_ID


# Shared global scope for evaluation
global_vars = globals().copy()

async def aexec(code, client, message):
    exec(
        "async def __aexec(client, message):\n"
        + "\n".join(f"    {line}" for line in code.split("\n")),
        global_vars,
    )
    return await global_vars["__aexec"](client, message)


async def edit_or_reply(msg: Message, **kwargs):
    func = msg.edit_text if msg.from_user.is_self else msg.reply
    spec = getfullargspec(func.__wrapped__).args
    await func(**{k: v for k, v in kwargs.items() if k in spec})


@app.on_edited_message(filters.command("eval") & filters.user(OWNER_ID))
@app.on_message(filters.command("eval") & filters.user(OWNER_ID))
async def executor(client: app, message: Message):
    if len(message.command) < 2:
        return await edit_or_reply(message, text="<b>ᴡʜᴀᴛ ʏᴏᴜ ᴡᴀɴɴᴀ ᴇxᴇᴄᴜᴛᴇ ʙᴀʙʏ ?</b>")
    cmd = message.text.split(" ", maxsplit=1)[1]
    t1 = time()
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    redirected_error = sys.stderr = StringIO()
    stdout, stderr, exc = None, None, None
    try:
        await aexec(cmd, client, message)
    except Exception:
        exc = traceback.format_exc()
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    evaluation = "\n"
    if exc:
        evaluation += exc
    elif stderr:
        evaluation += stderr
    elif stdout:
        evaluation += stdout
    else:
        evaluation += "Success"
    final_output = f"<b>⥤ ʀᴇsᴜʟᴛ :</b>\n<pre language='python'>{evaluation}</pre>"
    if len(final_output) > 4096:
        filename = "output.txt"
        with open(filename, "w+", encoding="utf8") as out_file:
            out_file.write(str(evaluation))
        t2 = time()
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("⏳", callback_data=f"runtime {t2-t1:.3f} Seconds")]]
        )
        await message.reply_document(
            document=filename,
            caption=f"<b>⥤ ᴇᴠᴀʟ :</b>\n<code>{cmd[:980]}</code>\n\n<b>⥤ ʀᴇsᴜʟᴛ :</b>\nAttached Document",
            quote=False,
            reply_markup=keyboard,
        )
        await message.delete()
        os.remove(filename)
    else:
        t2 = time()
        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("⏳", callback_data=f"runtime {round(t2 - t1, 3)} Seconds"),
                InlineKeyboardButton("🗑", callback_data=f"forceclose abc|{message.from_user.id}")
            ]]
        )
        await edit_or_reply(message, text=final_output, reply_markup=keyboard)


@app.on_callback_query(filters.regex(r"runtime"))
async def runtime_func_cq(_, cq):
    runtime = cq.data.split(None, 1)[1]
    await cq.answer(runtime, show_alert=True)


@app.on_callback_query(filters.regex("forceclose"))
async def forceclose_command(_, CallbackQuery):
    callback_data = CallbackQuery.data.strip()
    query, user_id = callback_data.split("|")
    if CallbackQuery.from_user.id != int(user_id):
        return await CallbackQuery.answer(
            "» ɪᴛ'ʟʟ ʙᴇ ʙᴇᴛᴛᴇʀ ɪғ ʏᴏᴜ sᴛᴀʏ ɪɴ ʏᴏᴜʀ ʟɪᴍɪᴛs ʙᴀʙʏ.", show_alert=True
        )
    await CallbackQuery.message.delete()
    await CallbackQuery.answer()


@app.on_edited_message(filters.command("sh") & filters.user(OWNER_ID))
@app.on_message(filters.command("sh") & filters.user(OWNER_ID))
async def shellrunner(_, message: Message):
    if len(message.command) < 2:
        return await edit_or_reply(message, text="<b>ᴇxᴀᴍᴩʟᴇ :</b>\n/sh git pull")
    text = message.text.split(None, 1)[1]
    output = ""
    try:
        shell = re.split(r""" (?=(?:[^'"]|'[^']*'|"[^"]*")*$)""", text)
        process = subprocess.Popen(shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        output = stdout.decode().strip() or stderr.decode().strip()
    except Exception as err:
        error_trace = traceback.format_exc()
        return await edit_or_reply(message, text=f"<b>ERROR :</b>\n<pre>{error_trace}</pre>")

    if not output:
        output = "None"
    if len(output) > 4096:
        with open("output.txt", "w+") as file:
            file.write(output)
        await app.send_document(
            message.chat.id,
            "output.txt",
            reply_to_message_id=message.id,
            caption="<code>Output</code>",
        )
        os.remove("output.txt")
    else:
        await edit_or_reply(message, text=f"<b>OUTPUT :</b>\n<pre>{output}</pre>")
    await message.stop_propagation()
