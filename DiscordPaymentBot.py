import json
import threading
import time

import discord
import pygsheets
from discord.ext import commands
from flask import Flask, send_from_directory

from PaymentSystem import payment_record, show_log, do_backup, show_backup, create_ppl, delete_ppl, payment_system, \
    wks_to_dict, payment_to_wks, payment_worker, log_worker, payment_queue, log_queue
from constants import *

app = Flask(__name__)
stop_event = threading.Event()


@app.route('/health_check.html')
def health_check():
    return send_from_directory(os.getcwd(), 'health_check.html')


def run_flask():
    app.run(host='0.0.0.0', port=8000)


def run(wks: pygsheets.Worksheet):
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        print(f"Current logged in user --> {bot.user}")
        await bot.change_presence(activity=discord.Game(name=BOT_STATUS))

    @bot.command(help="Show the bot information", brief="Bot information")
    async def info(message: commands.Context):
        await message.channel.send(BOT_DESCRIPTION)

    @bot.command(name="list", aliases=['l'], help="List out all payment records stored in the bot",
                 brief="List all payment records")
    async def show(message: commands.Context):
        await message.channel.send(payment_record(wks))

    @bot.command(help=f"Show the {LOG_SHOW_NUMBER} latest payment record inputs",
                 brief="Latest payment record inputs")
    async def log(message: commands.Context):
        await message.channel.send(show_log(LOG_SHOW_NUMBER))

    @bot.command(help=f"Show the {LONG_LOG_SHOW_NUMBER} latest payment record inputs",
                 brief="Latest payment record inputs")
    async def logall(message: commands.Context):
        await message.channel.send(show_log(LONG_LOG_SHOW_NUMBER))

    @bot.command(name='currencies', help="Show all the supported currencies", brief="All supported currencies")
    async def show_all_currencies(message: commands.Context):
        currency_text = '\n'.join([f"**{key}**: {value}" for key, value in SUPPORTED_CURRENCY.items()])
        await message.channel.send(currency_text)

    @bot.command(help="Backup the current payment record in a separate file", brief="Backup the payment record")
    async def backup(message: commands.Context):
        await message.channel.send("**Backup done**\n" + do_backup(wks))

    @bot.command(help="Show the backup records", brief="Show the backup records", hidden=True)
    async def showbackup(message: commands.Context):
        await message.channel.send(show_backup())

    @bot.command(help="Create a new user with a name", brief="Create a new user")
    async def create(message: commands.Context):
        if message.channel.id != PAYMENT_CHANNEL_ID:
            await message.channel.send("Please create in the **payment** channel")
            return
        if len(message.message.content.split()) < 2:
            await message.channel.send("Please input the name of the person you want to create")
            return
        person = message.message.content.split()[1]
        author = message.author.name
        if create_ppl(person, author, wks):
            await message.channel.send(f"### Person {person} created!\n{payment_record(wks)}")
            await bot.get_channel(LOG_CHANNEL_ID).send(f"{author}: Created new person: {person}")
        else:
            await message.channel.send(f"**Failed to create {person}!**\nPerson already exists.")

    @bot.command(help="Delete a user if he has no debts", brief="Delete a user")
    async def delete(message: commands.Context):
        if message.channel.id != PAYMENT_CHANNEL_ID:
            await message.channel.send("Please delete in the **payment** channel")
            return
        if len(message.message.content.split()) < 2:
            await message.channel.send("Please input the name of the person you want to delete")
            return
        target = message.message.content.split()[1]
        author = message.author.name
        if delete_ppl(target, author, wks):
            await message.channel.send(f"### Person {target} deleted!\n{payment_record(wks)}")
            await bot.get_channel(LOG_CHANNEL_ID).send(f"{author}: Deleted person: {target}")
        else:
            await message.channel.send(f"**Failed to delete {target}!**\nPerson not found or has not paid off yet.")

    @bot.command(help="Enters a payment record", brief="Enters a payment record")
    async def pm(message: commands.Context):
        if message.channel.id != PAYMENT_CHANNEL_ID:
            await message.channel.send("Please input the record in the **payment** channel")
            return
        await payment_system(bot, message, wks)

    @bot.command(help="Enters a payment record by averaging the amount", brief="Enters a payment record by averaging")
    async def pmavg(message: commands.Context):
        if message.channel.id != PAYMENT_CHANNEL_ID:
            await message.channel.send("Please input the record in the **payment** channel")
            return
        await payment_system(bot, message, wks, avg=True)

    bot.run(BOT_KEY)


if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    with open(SERVICE_ACCOUNT_FILE, 'w') as json_file:
        json.dump(GOOGLE_CRED, json_file, indent=2)

    # Link to the Google Sheet
    gc = pygsheets.authorize(service_file=SERVICE_ACCOUNT_FILE)
    sheet = gc.open_by_url(RECORD_SHEET_URL)
    record_wks = sheet.worksheet_by_title('Records')
    with open(PAYMENT_RECORD_FILE, 'w') as json_file:
        record = wks_to_dict(record_wks)
        if not record:
            raise Exception("Empty record sheet")
        json.dump(record, json_file, indent=2)

    # Start other threads
    payment_thread = threading.Thread(target=payment_worker, args=(record_wks, stop_event), daemon=True)
    payment_thread.start()
    log_thread = threading.Thread(target=log_worker, args=(stop_event,), daemon=True)
    log_thread.start()

    try:
        run(record_wks)
    except Exception as e:
        print(e)
    finally:
        stop_event.set()
        payment_queue.put(None)
        payment_queue.join()
        log_queue.put(None)
        log_queue.join()
        payment_to_wks(record_wks)
        open(SERVICE_ACCOUNT_FILE, 'w').close()
        open(PAYMENT_RECORD_FILE, 'w').close()
