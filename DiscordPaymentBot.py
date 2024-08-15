from discord.ext import commands
import discord

from ExchangeRateHandler import ExchangeRateHandler
from constants import *
from botInfo import *
import PMBotUI

import time


def payment_record_to_dict() -> dict:
    payment_data = {CENTRALIZED_PERSON: -1}
    with open(PAYMENT_RECORD_FILE, 'r', encoding='utf8') as file:
        for line in file:
            record = line.split()
            payment_data[record[0].lower()] = float(record[1])
    return payment_data


def write_log(message: str) -> None:
    with open(LOG_FILE, 'a', encoding="utf8") as file:
        file.write(message + "\n")


def show_log(num: int = -1) -> str:
    log_content = ""
    log_lines = []

    with open(LOG_FILE, 'r', encoding='utf8') as file:
        show_num = num if num > 1 else DEFAULT_LOG_SHOW_NUMBER
        for line in file:
            log_lines.append(line)
        for line in log_lines[-min(show_num, len(log_lines)):]:
            if log_content == "":
                if line != "\n":
                    log_content = line
            else:
                log_content += line
    return log_content


def read_last_log() -> list[str]:
    content = ""
    with open(LOG_FILE, 'r', encoding='utf8') as file:
        for line in file:
            content = line
    return content.split()


def payment_record() -> str:
    zero = take_money = need_pay = centralized_person = ""
    count = 0.0

    with open(PAYMENT_RECORD_FILE, 'r', encoding='utf8') as file:
        for line in file:
            record = line.split()
            count += float(record[1])
            if float(record[1]) == 0:
                zero += f"**{record[0]}** don\'t need to pay\n"
            elif float(record[1]) > 0:
                take_money += f"**{CENTRALIZED_PERSON}** needs to pay **{record[0]}** _${record[1]}_\n"
            else:
                need_pay += f"**{record[0]}** needs to pay **{CENTRALIZED_PERSON}** _${record[1][1:]}_\n"

        centralized_person = f"**{CENTRALIZED_PERSON}** "
        centralized_person += "doesn't need to pay" if count == 0 else \
                              f"{'needs to pay' if count > 0 else 'will receive'} ${abs(round(count, 3))} in total"

    zero = zero + "\n" if zero else zero
    take_money = take_money + "\n" if take_money else take_money
    need_pay = need_pay + "\n" if need_pay else need_pay

    payment_record_content = zero + take_money + need_pay + centralized_person
    return payment_record_content


def create_ppl(name: str, amount=0.0) -> bool:
    try:
        with open(PAYMENT_RECORD_FILE, 'a', encoding='utf8') as file:
            file.write(name.lower() + " " + str(amount) + "\n")
            return True
    except Exception as e:
        print(e)
        return False


def delete_ppl(target: str) -> bool:
    payment_data = {}

    with open(PAYMENT_RECORD_FILE, 'r', encoding='utf8') as file:
        for line in file:
            record = line.split()
            payment_data[record[0].lower()] = record[1]

    try:
        if payment_data[target] != '0.0':
            return False
        del payment_data[target]
    except KeyError:
        return False

    with open(PAYMENT_RECORD_FILE, "w+", encoding='utf8') as file:
        for name, amount in payment_data.items():
            file.write(name + ' ' + amount + "\n")
    return True


def owe(payment_data: dict, person_to_pay: str, person_get_paid: str, amount: float) -> str:
    if person_to_pay == person_get_paid:
        return ""
    if person_to_pay == CENTRALIZED_PERSON:
        target = person_get_paid
        add = True
    elif person_get_paid == CENTRALIZED_PERSON:
        target = person_to_pay
        add = False
    else:
        write_log("funtion owe: centralized person not found")
        return ""

    original = payment_data[target]
    current = round(original + amount if add else original - amount, ROUND_OFF_DP)
    payment_data[target] = current

    p = original > 0
    p0 = original == 0
    c = current > 0
    c0 = current == 0

    original = abs(original)
    current = abs(current)

    """
        p 0: jaga pay XXX __ -> XXX don't pay
        !p 0: XXX pay jaga __ -> XXX don't pay
        0 c: jaga pay XXX __ (new record)
        0 !c: XXX pay jaga __ (new record)
        
        p c: jaga pay XXX: __ -> __
        !p c: XXX pay jaga __ -> jaga pay XXX __
        p !c: jaga pay XXX __ -> XXX pay jaga __
        !p !c: XXX pay jaga: __ -> __
    """

    # readability pro max!!!
    if p and c0:
        return f"> -# {CENTRALIZED_PERSON} needs to pay {target} ${original} -→ {target} doesn't need to pay\n"
    elif not p and c0:
        return f"> -# {target} needs to pay {CENTRALIZED_PERSON} ${original} -→ {target} doesn't need to pay\n"
    elif p0 and c:
        return f"> -# {CENTRALIZED_PERSON} needs to pay {target} ${current} (new record)\n"
    elif p0 and not c:
        return f"> -# {target} needs to pay {CENTRALIZED_PERSON} ${current} (new record)\n"
    elif p and c:
        return f"> -# {CENTRALIZED_PERSON} needs to pay {target}: ${original} -→ ${current}\n"
    elif not p and c:
        return f"> -# {target} needs to pay {CENTRALIZED_PERSON} ${original} -→ " \
               f"{CENTRALIZED_PERSON} needs to pay {target} ${current}\n"
    elif p and not c:
        return f"> -# {CENTRALIZED_PERSON} needs to pay {target} ${original} -→ " \
               f"{target} needs to pay {CENTRALIZED_PERSON} ${current}\n"
    else:
        return f"> -# {target} needs to pay {CENTRALIZED_PERSON}: ${original} -→ ${current}\n"


def payment_handling(ppl_to_pay: str, ppl_get_paid: str, amount: float) -> str:
    update = ""
    payment_data = payment_record_to_dict()
    del payment_data[CENTRALIZED_PERSON]

    # main logic
    try:
        pay_list = ppl_to_pay.split(',')
        paid_list = ppl_get_paid.split(',')
        for each_to_pay in pay_list:
            for each_get_paid in paid_list:
                if each_get_paid == CENTRALIZED_PERSON:
                    update += owe(payment_data, each_to_pay, CENTRALIZED_PERSON, amount)
                elif each_to_pay == CENTRALIZED_PERSON:
                    update += owe(payment_data, CENTRALIZED_PERSON, each_get_paid, amount)
                else:
                    update += owe(payment_data, each_to_pay, CENTRALIZED_PERSON, amount) + \
                              owe(payment_data, CENTRALIZED_PERSON, each_get_paid, amount)
                update += "> \n" if len(paid_list) > 1 else ""
            update += "> \n" if len(pay_list) > 1 else ""
        update = update[:-3]
    except KeyError:
        print("Person not found.")
        return ""

    with open(PAYMENT_RECORD_FILE, "w+", encoding='utf8') as file:
        for name, amount in payment_data.items():
            file.write(name + ' ' + str(amount) + '\n')

    return update


def do_backup() -> None:
    with open(BACKUP_FILE, 'a', encoding='utf8') as bkup_file:
        bkup_file.write('[' + time.strftime('%Y-%m-%d %H:%M') + "]\n")
        with open(PAYMENT_RECORD_FILE, 'r', encoding='utf8') as pm_file:
            for line in pm_file:
                bkup_file.write(line)
        bkup_file.write("\n")


def show_backup() -> str:
    content = ""
    with open(BACKUP_FILE, 'r', encoding='utf8') as file:
        for line in file:
            content += line
    return content


def run():
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        print(f"Current logged in user --> {bot.user}")
        await bot.change_presence(activity=discord.Game(name=BOT_STATUS))

    @bot.command()
    async def info(message: commands.Context):
        await message.channel.send(BOT_DESCRIPTION)

    @bot.command(name="list")
    async def show(message: commands.Context):
        await message.channel.send(payment_record())

    @bot.command()
    async def log(message: commands.Context):
        await message.channel.send(show_log(LOG_SHOW_NUMBER))

    @bot.command()
    async def logall(message: commands.Context):
        await message.channel.send(show_log())

    @bot.command()
    async def backup(message: commands.Context):
        do_backup()
        write_log(f"\n---------------backup: [{time.strftime('%Y-%m-%d %H:%M')}]---------------")
        await message.channel.send("Backup done")
        await message.channel.send(show_backup())

    @bot.command()
    async def showbackup(message: commands.Context):
        await message.channel.send(show_backup())

    @bot.command()
    async def create(message: commands.Context):
        if create_ppl(message.message.content.split()[1]):
            await message.channel.send(f"### Person {message.message.content.split()[1]} created!\n{payment_record()}")
        else:
            await message.channel.send("Please input the name of the person to be created")

    @bot.command()
    async def delete(message: commands.Context):
        if delete_ppl(message.message.content.split()[1]):
            await message.channel.send(f"**Person {message.message.content.split()[1]} deleted!**\n{payment_record()}")
        else:
            await message.channel.send(f"**Fail to delete {message.message.content.split()[1]}!**\n"
                                       f"Person not found or has not paid off yet.")

    @bot.command()
    async def pm(message: commands.Context):
        async def single_pm():
            msg: list[str] = message.message.content.lower().split()
            if len(msg) >= 5:
                # Command line UI: e.g. !pm p1,p2 owe p3,p4 100 -CNY (reason)
                ppl_to_pay: str = msg[1].lower()
                for ppl in ppl_to_pay.split(','):
                    if ppl not in payment_data.keys().__str__().lower():
                        await message.channel.send("**Invalid input for provider!**")
                        return

                operation: str = msg[2].lower()
                if operation not in ["owe", "payback"]:
                    await message.channel.send("**Invalid payment operation!**")
                    return
                else:
                    operation_owe = operation == "owe"

                ppl_get_paid: str = msg[3].lower()
                if ppl_get_paid not in payment_data.keys().__str__().lower():
                    await message.channel.send("**Invalid input for receiver!**")
                    return

                try:
                    amount = float(msg[4])
                    if amount == 0.0:
                        await message.channel.send("**Invalid amount: amount cannot be zero!**")
                        return
                    amount = str(amount)
                except ValueError:
                    await message.channel.send("**Invalid input for amount!**")
                    return

                currency = UNIFIED_CURRENCY
                reason = ""
                if len(msg) > 5:
                    if msg[5].startswith('-'):
                        currency = msg[5][1:].upper()
                    if len(msg) > 6:
                        reason = " ".join(msg[6:])

                if ppl_get_paid in ppl_to_pay.split(','):
                    await message.channel.send("**Invalid input: one cannot pay himself!**")
                    return

            else:
                # graphic UI
                menu = PMBotUI.View(payment_data)
                menu.message = await message.send(view=menu)
                await menu.wait()

                ppl_to_pay = menu.pay_text
                operation_owe = menu.owe
                ppl_get_paid = menu.paid_text
                amount = menu.amount_text
                currency = menu.currency if menu.currency else UNIFIED_CURRENCY
                reason = menu.reason if menu.reason else ""

                if menu.cancelled:
                    return
                if not menu.finished:
                    await message.channel.send("**> Input closed. You take too long!**")
                    return

            handler = None
            if currency != UNIFIED_CURRENCY and currency in SUPPORTED_CURRENCY:
                handler = ExchangeRateHandler()
                amount = handler(currency, amount).split('.')
                amount = amount[0] + '.' + amount[1][:ROUND_OFF_DP]
                amount = "".join(amount.split(','))

            # log the record
            log_content = f"{message.author}: {ppl_to_pay} " \
                          f"{'owe' if operation_owe else 'pay back'} {ppl_get_paid} " \
                          f"${amount}{' ' + reason}"
            write_log(log_content)
            await log_channel.send(log_content)

            # switch pay & paid for pay back operation
            if not operation_owe:
                temp = ppl_to_pay
                ppl_to_pay = ppl_get_paid
                ppl_get_paid = temp

            # perform the payment operation
            update = payment_handling(ppl_to_pay, ppl_get_paid, float(amount))

            # error occurred
            if not update:
                await message.channel.send("**ERROR: Payment handling failed**")
                return

            await message.channel.send(f"__**Payment record successfully updated!**__\n`{log_content}`"
                                       f"\n> -# Updated records:\n{update}")

            undo_view = PMBotUI.UndoView()
            undo_view.message = await message.send(view=undo_view)

            if handler:
                handler.quit()

            await undo_view.wait()

            # handle undo operation
            if undo_view.undo:
                undo_update = "> -# Updated records:\n"
                undo_update += payment_handling(ppl_get_paid, ppl_to_pay, float(amount))
                await message.channel.send("**Undo has been executed!**\n" + undo_update)
                undo_log_content = f"{message.author}: undo **[**{log_content}**]**"
                write_log(undo_log_content)
                await log_channel.send(undo_log_content)

        if message.channel.id != PAYMENT_CHANNEL_ID:
            await message.channel.send("Please input the record in the **payment** channel")
            return

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        payment_data = payment_record_to_dict()
        # for each_pm in message.message.content.split('\n'):
        #     if each_pm:
        #         await single_pm()
        await single_pm()

    bot.run(BOT_KEY)


if __name__ == '__main__':
    run()
