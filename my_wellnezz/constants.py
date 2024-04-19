import platform

import colorama

name = 'myWellnezz'
author = 'AeonDave'
version = '1.2.0'
app_id = 'EC1D38D7-D359-48D0-A60C-D8C0B8FB9DF9'
os = platform.system()
logo = f'''         
{colorama.Fore.LIGHTBLACK_EX}                   {colorama.Fore.YELLOW} M""MMM""MMM""M{colorama.Fore.LIGHTBLACK_EX}          dP dP                                     
{colorama.Fore.LIGHTBLACK_EX}                   {colorama.Fore.YELLOW} M  MMM  MMM  M{colorama.Fore.LIGHTBLACK_EX}          88 88                                     
{colorama.Fore.LIGHTBLACK_EX}88d8b.d8b. dP    dP{colorama.Fore.YELLOW} M  MMP  MMP  M{colorama.Fore.LIGHTBLACK_EX} .d8888b. 88 88 88d888b. .d8888b. d888888b d888888b 
{colorama.Fore.LIGHTBLACK_EX}88'`88'`88 88    88{colorama.Fore.YELLOW} M  MM'  MM' .M{colorama.Fore.LIGHTBLACK_EX} 88ooood8 88 88 88'  `88 88ooood8    .d8P'    .d8P' 
{colorama.Fore.LIGHTBLACK_EX}88  88  88 88.  .88{colorama.Fore.YELLOW} M  `' . '' .MM{colorama.Fore.LIGHTBLACK_EX} 88.  ... 88 88 88    88 88.  ...  .Y8P     .Y8P    
{colorama.Fore.LIGHTBLACK_EX}dP  dP  dP `8888P88{colorama.Fore.YELLOW} M    .d  .dMMM{colorama.Fore.LIGHTBLACK_EX} `88888P' dP dP dP    dP `88888P' d888888P d888888P{colorama.Fore.YELLOW} v{version} by {colorama.Fore.RED}{author}
{colorama.Fore.LIGHTBLACK_EX}                .88{colorama.Fore.YELLOW} MMMMMMMMMMMMMM{colorama.Fore.LIGHTBLACK_EX}                                                    
{colorama.Fore.LIGHTBLACK_EX}            d8888P {colorama.Style.RESET_ALL}                                                    
'''

schema = 'https://'
base_url = 'mywellness.com'
api_book = '/v2/enduser/class/book'
api_search = '/v2/enduser/class/search'
api_search_app = '/Core/Facility'
api_book_app = '/Core/CalendarEvent'
