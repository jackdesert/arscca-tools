'''
This module publishes results located on your thumb drive to arscca.org.

The general flow is:
    1. Use this module to publish results to arscca.org
    2. Use bin/archive_results.py to make a copy of those results
'''

from getpass import getpass
import os
import pdb
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import requests

class AxwarePublisher:
    SITE = 'http://arscca.org/administrator'
    USERNAME = 'jackdesert'
    YEAR = 2022

    NEW_CATEGORY_PAGE = 'index.php?option=com_categories&task=category.add&extension=com_content'
    NEW_ARTICLE_PAGE = 'index.php?option=com_content&task=article.add'
    USB_DRIVE = '/media/usb'

    FILE_TO_SEARCH = '_fin_.htm' # The final results end in this
    RESULT_TYPES = {'fin': 'Final',
                    'pax': 'PAX',
                    'raw': 'Raw',
                    'sum': 'Summary'}

    def __init__(self):
        self._welcome()
        self.event_short_name = input('Enter event name, such as:  Event 1 (Slide Park)\n  ')
        # Password is set later
        self.__passwd = None

        # WebDriver is created later so that browser does not distract user
        self._driver  = None

        # _dir is set in _get_directory
        self._dir     = None
        self._get_directory()

    def publish(self):
        print(f'\n\nFull event Name will be:\n  {self._event_full_name}')
        print(f'\nData directory:\n  {self._dir}')
        time.sleep(5) # Humans require time to absorb information
        self._login()
        self._create_event_category()
        self._create_articles()
        print('Done')


    def _welcome(self):
        print("\nEVENT PUBLISHER by Jack Desert")
        print(f'site: {self.SITE}\n')

    @property
    def _event_full_name(self):
        return f'{self.YEAR} Solo II {self.event_short_name}'

    def _login(self):
        self.__passwd = getpass(f'\nIf you are satisfied, enter password for Joomla user {self.USERNAME}\n  ')
        print('Opening Browser')

        self._driver = webdriver.Firefox()

        print('Logging in to Joomla')
        self._driver.get(self.SITE)
        username = self._driver.find_element_by_name('username')
        username.clear()
        username.send_keys(self.USERNAME)

        passwd = self._driver.find_element_by_name('passwd')
        passwd.clear()
        passwd.send_keys(self.__passwd)
        passwd.send_keys(Keys.RETURN)
        time.sleep(1)

    def _create_event_category(self):
        """
        An example category is "2022 Solo II Event 14"
        """
        print(f'\nCreating event category:\n  {self._event_full_name}')

        self._driver.get(f'{self.SITE}/{self.NEW_CATEGORY_PAGE}')
        title = self._driver.find_element_by_id('jform_title')
        title.clear()
        title.send_keys(self._event_full_name)

        # Select Parent
        self._select_option_via_search('jform_parent_id_chzn', f'{self.YEAR} Results')

        self._javascript_save('category')
        time.sleep(1)


    def _get_directory(self):
        directories = set()

        for item in os.listdir(self.USB_DRIVE):
            item_path = f'{self.USB_DRIVE}/{item}'
            if os.path.isfile(item_path):
                # We want directories, not files
                continue

            if not item.startswith('event'):
                # We only want directories that start with "event"
                continue

            for subitem in os.listdir(item_path):
                if os.path.isfile(f'{item_path}/{subitem}') and self.FILE_TO_SEARCH in subitem:
                    directories.add(item)

        print('')

        directories = sorted(directories)
        if not directories:
            print('ERROR: No directories containing *{self.FILE_TO_SEARCH} in {self.USB_DRIVE}')
            exit()

        print(f'Which Directory in {self.USB_DRIVE} contains the results?')
        for index_zero_based, item in enumerate(directories):
            print(f'  {index_zero_based + 1}. {item}')

        dir_index = int(input()) - 1
        self._dir = f'{self.USB_DRIVE}/{directories[dir_index]}'

    def _html_content(self, result_type):
        if not result_type in self.RESULT_TYPES:
            print(f'ERROR: {result_type} not in {self.RESULT_TYPES}')
            exit()

        if not self._dir:
            print(f'ERROR: directory not set')
            exit()

        for filename in os.listdir(self._dir):
            if f'_{result_type}_.htm' in filename:
                with open(f'{self._dir}/{filename}') as fh:
                    return fh.read()

        print(f'ERROR: Filename matching {result_type} not found in {self._dir}')
        exit()

    def _create_articles(self):
        for result_type in self.RESULT_TYPES:
            content = self._html_content(result_type)
            self._create_article(result_type, content)

    def _create_article(self, result_type, content):
        self._driver.get(f'{self.SITE}/{self.NEW_ARTICLE_PAGE}')

        title = self._driver.find_element_by_xpath("//input[@id='jform_title']")
        prepend = self._event_full_name
        article_name = f'{prepend} {self.RESULT_TYPES[result_type]}'
        print(f'\nCreating article:\n  {article_name}')
        title.send_keys(article_name)

        # Select category
        self._select_option_via_search('jform_catid_chzn', self._event_full_name)

        self._toggle_editor()

        html = self._html_content(result_type)

        # Escape the html so it works as a javascript string
        # that can be referenced from .execute_script
        html_escaped = html.replace('"', '\"').replace("'", '\"').replace('\n', '\\n')

        # send_keys is slow when sending zillions of keys,
        # so we use javascript instead
        self._driver.execute_script(f"var area = document.getElementById('jform_articletext');area.value = '{html_escaped}';")

        self._javascript_save('article')

        time.sleep(1)


    def _javascript_save(self, page_type):
        self._driver.execute_script(f'Joomla.submitbutton("{page_type}.save")')

    def _toggle_editor(self):
        print('NOT TOGGLING EDITOR BECAUSE tinyMCE DISABLED')
        return
        js = "tinyMCE.execCommand('mceToggleEditor', false, 'jform_articletext')"
        self._driver.execute_script(js)

    # Joomla uses a search box with their select field.
    # If you search for something and it matches, you can simply press ENTER
    # to select it
    #
    def _select_option_via_search(self, containing_div_id, search_text):
        search = self._driver.find_element_by_xpath(f"//div[@id='{containing_div_id}']//input")
        search.send_keys(search_text)
        search.send_keys(Keys.RETURN)




if __name__ == '__main__':
    pub = AxwarePublisher()
    pub.publish()
