import discord
from discord.ext import commands
import aiohttp
import requests as r
import cachecontrol
import time
from fuzzywuzzy import fuzz, process

class Netrunner:
    """comment"""

    def __init__(self, bot):
        self.bot = bot
        self.base_url = 'https://netrunnerdb.com/api/2.0/public/'
        self.session = cachecontrol.CacheControl(r.Session())
        self.faction_codes = {
                'shaper': 'Shaper',
                'haas-bioroid': 'Haas-Bioroid',
                'jinteki': 'Jinteki',
                'weyland-consortium': 'Weyland Consortium',
                'anarch': 'Anarch',
                'apex': 'Apex',
                'sunny-lebeau': 'Sunny Lebeau',
                'neutral-runner': 'Neutral',
                'neutral-corp': 'Neutral',
                'adam': 'Adam', 
                'criminal': 'Criminal',
                'nbn': 'NBN'
                }

    def type_formatting(self, blob):
        type_code = blob.get('type_code', None)
        if type_code == 'agenda':
            return ''.join(['Advancements: ', str(blob.get('advancement_cost')), ', Agenda Points: ', str(blob.get('agenda_points'))])
        elif type_code == 'program':
            return ''.join(['Install: ', str(blob.get('cost')), ', Strength: ', str(blob.get('strength', '-'))])
        elif type_code == 'ice':
            return_string = ''.join(['Rez: ', str(blob.get('cost')), ', Strength: ', str(blob.get('strength'))])
            if blob.get('trash_cost', None) is not None:
                return_string += ''.join([', Trash Cost: ', str(blob.get('trash_cost'))])
            return return_string
        elif type_code == 'identity':
            if blob.get('influence_limit') is None:
                influence = '∞'
            else: 
                influence = str(blob.get('influence_limit'))
            return_string = ''.join(['Deck Size: ', str(blob.get('minimum_deck_size')), ', Influence: ', influence])
            if blob.get('base_link', None) is not None:
                return_string += ''.join([', Link: ', str(blob.get('base_link'))])
            return return_string
        elif type_code in ['asset', 'upgrade']:
            return ''.join(['Rez: ', str(blob.get('cost')), ', Trash Cost: ', str(blob.get('trash_cost'))])
        elif type_code in ['operation', 'event']: 
            return_string = ''.join(['Cost: ', str(blob.get('cost'))])
            if blob.get('trash_cost', None) is not None:
                return_string += ''.join([', Trash Cost: ', str(blob.get('trash_cost'))])
            return return_string
        elif type_code in ['hardware', 'resource']:
            return ''.join(['Install: ', str(blob.get('cost'))])
        else:
            return ''

    def _call_endpoint(self, endpoint):
        return self.session.get(''.join([self.base_url, endpoint])).json()['data']

    def format_response(self, blob):
        return_string = ''
        if blob.get('uniqueness'):
            return_string += '♦ '
        return_string += ''.join(['**', blob.get('title', ''), '**\n'])
        return_string += ''.join(['*', self.faction_codes[blob.get('faction_code', None)], '*\n'])

        return_string += ''.join(['*', blob.get('type_code', '').title(), '*'])
        if blob.get('keywords', None) is not None:
            return_string += ''.join([': ', '*', blob.get('keywords'), '*'])
        if blob.get('faction_cost', None) is not None:
            return_string += ''.join([', Influence: ', str(blob.get('faction_cost'))])
        return_string +='\n'
        
        return_string += self.type_formatting(blob)
        # Card Type Formatting
        # so to get emoji to show up, go on server
        # type in "\:EMOJINAME:" in chat
        # that's the mention part
        card_text = blob.get('text', '')
        return_string += ''.join(['\n', card_text, '\n'])
        if blob.get('flavor', None) is not None:
            return_string += ''.join(['\n', '*', blob.get('flavor', ''), '*\n'])
        return return_string
        
    @commands.command()
    async def card(self, *args):
        """Find card by <title>"""

        title = ' '.join(args)
    
        if len(title) == 0:
            await self.bot.say('Please include a title with your request! `!card TITLE`')
        else:
            resp = self._call_endpoint('cards')

            title_crosswalk = {x['title']:x['code'] for x in resp}
            full_crosswalk = {x['code']:x for x in resp}

            card_titles = list(title_crosswalk.keys())
            possible_cards = process.extract(title, card_titles, 
                limit=10, scorer=fuzz.token_set_ratio)
            for card in [x[0] for x in possible_cards]: 
              if str(title).lower() == card.lower():
                  highest_card = title_crosswalk[card]
                  break
              else:
                  highest_card = title_crosswalk[possible_cards[0][0]]

            potential_matches = [x[0] for x in possible_cards if x[1] >= 90]

            await self.bot.say(self.format_response(full_crosswalk[highest_card]))
            if len(potential_matches) > 1:
                await self.bot.say('I also found the following cards: ' + ', '.join(potential_matches[1:]))  

    @commands.command()
    async def fullart(self, *args):
        """Show card art by <title>"""

        title = ' '.join(args)
        card_art_url = 'https://netrunnerdb.com/card_image/'

        if len(title) == 0:
            await self.bot.say('Please include a title with your request! `!fullart TITLE`')
        else:
            resp = self._call_endpoint('cards')
            title_crosswalk = {x['title']:x['code'] for x in resp}
            full_crosswalk = {x['code']:x for x in resp}

            card_titles = list(title_crosswalk.keys())
            possible_cards = process.extract(title, card_titles,
                    limit=10, scorer=fuzz.token_set_ratio)
            for card in [x[0] for x in possible_cards]:
                if str(title).lower() == card.lower():
                    highest_card = title_crosswalk[card]
                    break
                else:
                    highest_card = title_crosswalk[possible_cards[0][0]]

            potential_matches = [x[0] for x in possible_cards if x[1] >= 90]

            #await self.bot.say(full_crosswalk[highest_card]['image_url'])
            await self.bot.say(''.join([card_art_url, str(highest_card), '.png']))
            if len(potential_matches) > 1:
                await self.bot.say('I also found the following cards: ' + ', '.join(potential_matches[1:]))


def setup(bot):
    bot.add_cog(Netrunner(bot))
