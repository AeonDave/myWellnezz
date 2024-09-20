import importlib.metadata
import platform

import colorama as c

name = 'myWellnezz'
author = importlib.metadata.metadata(name)['Author']
version = importlib.metadata.version(name)
app_id = 'EC1D38D7-D359-48D0-A60C-D8C0B8FB9DF9'
os = platform.system()
logo = f'''         
{c.Fore.LIGHTBLACK_EX}                   {c.Fore.YELLOW} M""MMM""MMM""M{c.Fore.LIGHTBLACK_EX}          dP dP                                     
{c.Fore.LIGHTBLACK_EX}                   {c.Fore.YELLOW} M  MMM  MMM  M{c.Fore.LIGHTBLACK_EX}          88 88                                     
{c.Fore.LIGHTBLACK_EX}88d8b.d8b. dP    dP{c.Fore.YELLOW} M  MMP  MMP  M{c.Fore.LIGHTBLACK_EX} .d8888b. 88 88 88d888b. .d8888b. d888888b d888888b 
{c.Fore.LIGHTBLACK_EX}88'`88'`88 88    88{c.Fore.YELLOW} M  MM'  MM' .M{c.Fore.LIGHTBLACK_EX} 88ooood8 88 88 88'  `88 88ooood8    .d8P'    .d8P' 
{c.Fore.LIGHTBLACK_EX}88  88  88 88.  .88{c.Fore.YELLOW} M  `' . '' .MM{c.Fore.LIGHTBLACK_EX} 88.  ... 88 88 88    88 88.  ...  .Y8P     .Y8P    
{c.Fore.LIGHTBLACK_EX}dP  dP  dP `8888P88{c.Fore.YELLOW} M    .d  .dMMM{c.Fore.LIGHTBLACK_EX} `88888P' dP dP dP    dP `88888P' d888888P d888888P{c.Fore.YELLOW} v{version} by {c.Fore.RED}{author}
{c.Fore.LIGHTBLACK_EX}                .88{c.Fore.YELLOW} MMMMMMMMMMMMMM{c.Fore.LIGHTBLACK_EX}                                                    
{c.Fore.LIGHTBLACK_EX}            d8888P {c.Style.RESET_ALL}                                                    
'''

schema = 'https://'
base_url = 'mywellness.com'
api_book = '/v2/enduser/class/book'
api_search = '/v2/enduser/class/search'
api_search_app = '/Core/Facility'
api_book_app = '/Core/CalendarEvent'
