### IMPORTS        ############################################################
import typing
from typing import Optional, Union
import random
from time import sleep
from enum import Enum

import discord
from discord.emoji import Emoji
from discord.enums import ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands

from game import Game
from steam_scrape import get_games_list, SearchFilter

###### CONSTANTS        #######################################################
TOKEN_FILE = '.token'
FILTER_CHOICES = [SearchFilter.BASE, SearchFilter.POPULAR, SearchFilter.BEST, SearchFilter.POPULAR_NEW]
GAMES = {}

class Choice(Enum):
    A = 0,
    B = 1,
    HIGHER = 0,
    LOWER = 1

###### VARS             #######################################################
user_scores = {}

###### UTILS            #######################################################
def random_game(type: SearchFilter = SearchFilter.BASE) -> Game:
    '''
    Gets a random game from the GAMES list and instantiates it as a Game object
    '''
    try:
        return GAMES[type][ random.randint( 0, len(GAMES[type]) - 1 ) ]
    except:
        return random_game(SearchFilter.BASE)


async def btn_callback(interaction: discord.Interaction, game_a: Game, game_b: Game, choice: Choice, game_filter: SearchFilter):
    '''
    Triggered when the user clicks an Option button.
    Check if their answer was correct or wrong and display it as a discord message.
    '''
    # track message id and user id
    message_id = interaction.message.id
    user_id = interaction.user.id

    # message header
    message = f'**{game_a.name} 🆚 {game_b.name}**\n\n'

    # display the player's choice
    chosen_game = f'🇦 - {game_a.name}' if choice is Choice.A else f'🇧 - {game_b.name}'
    message += f'You chose {chosen_game}! \n\n'

    # show player counts for both games
    message += f'🇦 has **{game_a.players_current:,}** players right now.\n\n'
    message += f'🇧 has **{game_b.players_current:,}** current players...\n'

    # check if the player's choice has more players
    if (
        (choice is Choice.A and game_a.players_current > game_b.players_current)
        or (choice is Choice.B and game_b.players_current > game_a.players_current)
    ):
    # Correct Answer
        # increase the player's score by 1
        if user_id in user_scores:
            user_scores[user_id] += 1
        else:
            user_scores[user_id] = 1

        message += '\n**CORRECT!!**'                                    # display victory message
        message += f'\n**Your Score: {user_scores[user_id]}**'          # display user's current score
        view = NextRound(game_filter)                                   # update UI View to show Next Round controls

    # Wrong Answer
    else:
        message += '\n**wrong :(**'                                     # display game over message
        view = RestartGame()                                            # update UI View to show Game Over controls
        message += f'\n**Total Score: {user_scores[user_id]}**'         # display total score before resetting it
        user_scores[user_id] = 0                                        # reset user's score
        
    # discord response
    await interaction.response.edit_message(content=message, view=view)


###### UI Classes        ######################################################
class MyButton(discord.ui.View):
    def __init__(self, label:str, url:str = '', emoji:str = '🌜') -> None:
        super().__init__()
        # btn = discord.ui.Button(label=label)
        self.add_item(discord.ui.Button(label=label, url=url, emoji=emoji, style=discord.ButtonStyle.secondary))
    
    @discord.ui.button(label='Detonate', style=discord.ButtonStyle.primary, emoji='💥')
    async def button(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = interaction.message
        button.disabled = True
        button.label = "You blew up the world :("
        
        await interaction.response.send_message("You clicked the detonate button!!! AAAAAA!!!")
        await msg.edit(view=self) # OR await interaction.followup.send()



class HigherLowerButton(discord.ui.Button):
    '''
    UI Button that represents a game choice (game A or B / higher or lower)
    '''
    def __init__(self, label: str, choice: Choice, game_a: Game, game_b: Game, game_filter: SearchFilter):
        emoji = '🇦' if choice is Choice.A else '🇧'
        self.game = game_a if choice is Choice.A else game_b
        self.choice = choice
        self.game_a = game_a
        self.game_b = game_b
        self.game_filter = game_filter

        super().__init__(label=label, emoji=emoji, style=discord.ButtonStyle.primary)
    

    # callback when clicking the button
    async def callback(self, interaction: discord.Interaction):
        await btn_callback(interaction, self.game_a, self.game_b, self.choice, self.game_filter)


# Higher Or Lower Buttons
class HigherOrLower(discord.ui.View):
    def __init__(self, game_a:Game, game_b: Game, game_filter: SearchFilter, timeout: float | None = 180):
        super().__init__(timeout=timeout)

        # btn_a = discord.ui.Button(label=game_a.name, emoji='🇦', style=discord.ButtonStyle.primary)
        btn_a = HigherLowerButton(game_a.name, Choice.A, game_a, game_b, game_filter)
        btn_b = HigherLowerButton(game_b.name, Choice.B, game_a, game_b, game_filter)

        # button callbacks
        async def btn_a_callback(interaction: discord.Interaction):
            message_id = interaction.message.id
            message = f'**{game_a.name} 🆚 {game_b.name}**\n\n'
            
            await interaction.response.edit_message(content=message, view=None)

            message += f'You chose 🇦 ! \n\n🇦 has **{game_a.players_current:,}** players right now.\n\n'
            
            sleep(1)
            await interaction.followup.edit_message(message_id, content=message, view=None)

            message += f'🇧 has **{game_b.players_current:,}** current players...\n'
            
            sleep(1)
            await interaction.followup.edit_message(message_id, content=message, view=None)

            if game_a.players_current > game_b.players_current:
                message += '\n**CORRECT!!**'
            else:
                message += '\n**wrong :(**'
            
            sleep(1)

            # await interaction.response.send_message(message)
            # await interaction.response.edit_message(content=message, view=None)
            await interaction.followup.edit_message(message_id, content=message, view=None)
            
    
        
        # assign callbacks
        # btn_a.callback = btn_a_callback
        # btn_b.callback = btn_b_callback

        # add the buttons to the UI
        self.add_item(btn_a)
        self.add_item(btn_b)

# Next Round
class NextRound(discord.ui.View):
    def __init__(self, game_filter: SearchFilter, *, timeout: float | None = 180):
        super().__init__(timeout=timeout)

        btn = discord.ui.Button(label='Next Round!', style=ButtonStyle.green, emoji='⏩')
        async def button_callback(interaction: discord.Interaction):
            await play_game(interaction, game_filter)
            # msg = interaction.message
            # ctx = bot.get_context(msg)
            # await bot.invoke(bot.get_command('play'))
            # await play(bot, interaction)
            # await play(interaction)
        
        btn.callback = button_callback
        self.add_item(btn)

# Restart
class RestartGame(discord.ui.View):
    def __init__(self, *, timeout: float | None = 180):
        super().__init__(timeout=timeout)

        btn = discord.ui.Button(label='Try again!', style=ButtonStyle.secondary, emoji='🔁')
        async def button_callback(interaction: discord.Interaction, game_filter: SearchFilter = SearchFilter.BASE):
            # fetching random game ID and title
            game_data_a = random_game()
            game_data_b = random_game()

            # make sure that both games are different
            if game_data_a['id'] == game_data_b['id']:
                game_data_b = random_game()

            # creating Game objects
            game_a = Game(game_data_a['id'], game_data_a['title'])
            game_b = Game(game_data_b['id'], game_data_b['title'])

            # game1 = Game('440', 'Team Fortress 2')
            # game2 = Game('312530', 'Duck Game')

            message = '**WHICH GAME HAS MORE PLAYERS RIGHT NOW?**\n\n'
            message += f'🇦 {game_a.name}\n{game_a.game_url}'
            message += '\n\n🆚\n\n'
            message += f'🇧 {game_b.name}\n{game_b.game_url}'
            message += '\n\n`make your choice...`'

            await interaction.response.send_message(message, view=HigherOrLower(game_a=game_a, game_b=game_b, game_filter=game_filter))
    
        btn.callback = button_callback
        self.add_item(btn)



###### Creating the bot! ######################################################
# bot = commands.Bot(command_prefix='???', intents = discord.Intents.all())
### Creating the bot!
class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='btn_', intents=intents)
        self.synced = False

    # on_ready event l think
    async def setup_hook(self) -> None:
        print("Fetching Steam game charts!")
        
        # Use this to update the bot username and avatar
        # with open("icon.png", "rb") as image:
        #     f = image.read()
        #     b = bytearray(f)
        #     await bot.user.edit(avatar=b, username="Steam Charts Game")

        print(bot.user.name)

        # Fetching ALL games
        global GAMES
        GAMES[SearchFilter.BASE] = get_games_list(SearchFilter.BASE)
        GAMES[SearchFilter.POPULAR] = get_games_list(SearchFilter.POPULAR)
        GAMES[SearchFilter.BEST] = get_games_list(SearchFilter.BEST)
        GAMES[SearchFilter.POPULAR_NEW] = get_games_list(SearchFilter.POPULAR_NEW)


        print(f'>>> fetched {len(GAMES[SearchFilter.BASE])} base steam games.')
        print(f'>>> fetched {len(GAMES[SearchFilter.POPULAR])} popular steam games.')
        print(f'>>> fetched {len(GAMES[SearchFilter.BEST])} highly-rated steam games.')
        print(f'>>> fetched {len(GAMES[SearchFilter.POPULAR_NEW])} popular new steam games.')

        # await self.wait_until_ready()

        if not self.synced:
            self.synced = await self.tree.sync(guild=discord.Object(id=349267379991347200))
            print(f'Synced {len(self.synced)} slash commands for {self.user} @ server 349267379991347200')
    
    # error handling
    async def on_command_error(self, ctx, error) -> None:
        await ctx.reply(error, ephemeral=True)

bot = Bot()


###### COMMANDS        #######################################################
async def play_game(interaction: discord.Interaction, game_filter: SearchFilter = SearchFilter.BASE):
    # fetching random game ID and title
    game_data_a = random_game(game_filter)
    game_data_b = random_game(game_filter)

    # make sure that both games are different
    if game_data_a['id'] == game_data_b['id']:
        game_data_b = random_game(game_filter)

    # creating Game objects
    game_a = Game(game_data_a['id'], game_data_a['title'])
    game_b = Game(game_data_b['id'], game_data_b['title'])

    # setting player score (if they don't have one yet)
    if interaction.user.id not in user_scores:
        user_scores[interaction.user.id] = 0

    # displaying the Game UI
    message = f'Round #{user_scores[interaction.user.id] + 1}\n\n'
    message += '**WHICH GAME HAS MORE PLAYERS RIGHT NOW?**\n\n'
    message += f'🇦 {game_a.name}\n{game_a.game_url}'
    message += '\n\n🆚\n\n'
    message += f'🇧 {game_b.name}\n{game_b.game_url}'
    message += '\n\n`make your choice...`'

    # sending the message and Buttons UI
    await interaction.response.send_message(message, view=HigherOrLower(game_a=game_a, game_b=game_b, game_filter=game_filter))

@bot.command()
async def sync(ctx, self) -> None:
    synced = await ctx.bot.tree.sync(ctx.guild)
    await ctx.send(f'Synced {len(synced)} commands')


@bot.tree.command(name="buttons", description='gonna try to add some buttons here', guild=discord.Object(id=349267379991347200))
@app_commands.describe(buttons = 'How many buttons do you want?')
@app_commands.describe(button_label = 'Text to display on the button 📝')
@app_commands.describe(button_url = 'Link to open when pressing the button🌐')
async def buttons(interaction: discord.Interaction, buttons:int = 1, button_label:str = 'Label', button_url:str = 'https://www.freelancepolice.org'):
    await interaction.response.send_message(f'trying to put {buttons} buttons here', view=MyButton(button_label, button_url))
    

@bot.tree.command(name='play', description='Play a game of Steam: Higher or Lower!', guild=discord.Object(id=349267379991347200))
@app_commands.describe(filter='What type of games do you want to play with?')
@app_commands.choices(filter=[
    app_commands.Choice(name = 'Default / Hot Games', value = 0),
    app_commands.Choice(name = 'Popular Games', value = 1),
    app_commands.Choice(name = 'Highest Rated Games', value = 2),
    app_commands.Choice(name = 'Popular New Releases', value = 3)
])
async def play(interaction: discord.Interaction, filter: int = 0):
    # debug
    
    print(filter)
    choice = FILTER_CHOICES[filter]
    print(choice)
    print(choice.value)

    # fetching random game ID and title
    game_data_a = random_game(choice)
    game_data_b = random_game(choice)

    # make sure that both games are different
    if game_data_a['id'] == game_data_b['id']:
        game_data_b = random_game(choice)

    # creating Game objects
    game_a = Game(game_data_a['id'], game_data_a['title'])
    game_b = Game(game_data_b['id'], game_data_b['title'])

    # setting player score (if they don't have one yet)
    if interaction.user.id not in user_scores:
        user_scores[interaction.user.id] = 0

    # displaying the Game UI
    message = f'Round #{user_scores[interaction.user.id] + 1}\n\n'
    message += '**WHICH GAME HAS MORE PLAYERS RIGHT NOW?**\n\n'
    message += f'🇦 {game_a.name}\n{game_a.game_url}'
    message += '\n\n🆚\n\n'
    message += f'🇧 {game_b.name}\n{game_b.game_url}'
    message += '\n\n`make your choice...`'

    # sending the message and Buttons UI
    await interaction.response.send_message(message, view=HigherOrLower(game_a=game_a, game_b=game_b, game_filter=choice))



###### RUNNING THE BOT #################################################
if __name__ == "__main__":
    print("_____________BUTTONS INITIALISED_____________")
    with open(TOKEN_FILE, 'r') as f:
        token = f.read()
    
    bot.run(token)