import discord
from discord.ext import commands
import aiohttp
import requests as r
import cachecontrol
import time
from fuzzywuzzy import fuzz, process

class Netrunner:
    """Netrunner!"""

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

    def _get_crosswalks(self):
        resp = self._call_endpoint('cards')
        title_crosswalk = {x['title']:x['code'] for x in resp}
        full_crosswalk = {x['code']:x for x in resp}
        return title_crosswalk, full_crosswalk

    def _card_match(self, title_crosswalk, full_crosswalk, title):
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
        return highest_card, potential_matches


    def _format_response(self, blob, in_mwl):
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
        if in_mwl is not None:
            return_string += ''.join(['\n', in_mwl])
        return return_string

    def _check_mwl(self, highest_card):
        resp = self._call_endpoint('mwl')
        active = [version for version in resp if version['active']]
        active_part = [active[0]['cards']]

        mwl_name = active[0]['name']
        mwl_date = active[0]['date_start']
        current_mwl = mwl_name + ' (' + mwl_date + ')'

        restricted_cards = [card[0] for card in active_part[0].items() if card[1].get('is_restricted')]
        banned_cards = [card[0] for card in active_part[0].items() if card[0] not in restricted_cards]
        if highest_card in restricted_cards:
            return ':unicorn: **Restricted** as of ' + current_mwl
        elif highest_card in banned_cards:
            return ':unicorn: **Banned** as of ' + current_mwl
        else:
            return None

        
    @commands.command()
    async def card(self, *args):
        """Find card by <title>"""

        title = ' '.join(args)
    
        if len(title) == 0:
            await self.bot.say('Please include a title with your request! `!card TITLE`')
        else:
            title_crosswalk, full_crosswalk = self._get_crosswalks()
            highest_card, potential_matches = self._card_match(title_crosswalk, 
                    full_crosswalk, title)
            in_mwl = self._check_mwl(highest_card)
            await self.bot.say(self._format_response(full_crosswalk[highest_card], in_mwl))
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
            title_crosswalk, full_crosswalk = self._get_crosswalks()
            highest_card, potential_matches = self._card_match(
                    title_crosswalk,
                    full_crosswalk,
                    title)

            if 'image_url' in full_crosswalk[highest_card].keys():
                await self.bot.say(full_crosswalk[highest_card]['image_url'])
            else:
                await self.bot.say(''.join([card_art_url, str(highest_card), '.png']))
            if len(potential_matches) > 1:
                await self.bot.say('I also found the following cards: ' + ', '.join(potential_matches[1:]))

    @commands.command()
    async def mwl(self, *args):
        """Details current MWL cards"""

        mwl_cards = {
                'runner': {
                    'restricted': [],
                    'banned': []
                    },
                'corp': {
                    'restricted': [],
                    'banned': []
                    }
                }
        _, full_crosswalk = self._get_crosswalks()
        resp = self._call_endpoint('mwl')
        active_part = [version['cards'] for version in resp if version['active']]
        for card in active_part[0].items():
            full_card_info = full_crosswalk[card[0]]
            if card[1].get('is_restricted', None):
                if full_card_info['side_code'] == 'runner':
                    mwl_cards['runner']['restricted'].append(full_card_info['title'])
                else:
                    mwl_cards['corp']['restricted'].append(full_card_info['title'])
            else:
                if full_card_info['side_code'] == 'runner':
                    mwl_cards['runner']['banned'].append(full_card_info['title'])
                else:
                    mwl_cards['corp']['banned'].append(full_card_info['title'])
        
        def format_text(front_text, cards):
            return '**' + front_text + '**' + ', '.join(sorted(cards))

        runner_restricted = format_text('Runner Restricted Cards: ', mwl_cards['runner']['restricted'])
        runner_banned = format_text('Runner Banned Cards: ', mwl_cards['runner']['banned'])
        corp_restricted = format_text('Corp Restricted Cards: ', mwl_cards['corp']['restricted'])
        corp_banned = format_text('Corp Banned Cards: ', mwl_cards['corp']['banned'])
        
        await self.bot.say('\n\n'.join([runner_restricted, corp_restricted, runner_banned, corp_banned]))

    @commands.command()
    async def unicorn(self):
        await self.bot.say(':unicorn:')


def setup(bot):
    bot.add_cog(Netrunner(bot))
