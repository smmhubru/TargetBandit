# -*- coding: utf8 -*-
import numpy as np
from scipy.stats import beta
import matplotlib.pyplot as plt
from threading import Timer, Lock
import time
import vk
import webbrowser

from asciimatics.widgets import Frame, MultiColumnListBox, Layout, VerticalDivider, Divider, Text, Button, TextBox, Widget
from asciimatics.effects import Mirage
from asciimatics.renderers import FigletText
from asciimatics.scene import Scene
from asciimatics.screen import Screen
from asciimatics.exceptions import ResizeScreenError, NextScene, StopApplication
import sys

#complie file with command, version 0.1.2
# pyinstaller --onedir --add-data "C:/Users/simen/PycharmProjects/Bandit/venv/Lib/site-packages/pyfiglet;./pyfiglet" targetbandit.py
# use --onefile flag for single exe file
# OSX: pyinstaller --onedir --add-binary='/System/Library/Frameworks/Tk.framework/Tk':'tk' --add-binary='/System/Library/Frameworks/Tcl.framework/Tcl':'tcl' --add-data='/Users/sergo/PycharmProjects/TargetBandit/venv/lib/python3.7/site-packages/pyfiglet/':'pyfiglet' targetbandit.py

def rbeta(alpha, beta, size=None):
    """Random beta variates."""
    from scipy.stats.distributions import beta as sbeta
    return sbeta.ppf(np.random.random(size), alpha, beta)
    # return np.random.beta(alpha, beta, size)


class PeriodicTimer(object):
    """A periodic task running in threading"""

    def __init__(self, interval=None, function=None, *args, **kwargs):
        self._lock = Lock()
        self._timer = None
        self.function = function
        self.interval = interval
        self.args = args
        self.kwargs = kwargs
        self._stopped = True
        # if kwargs.pop('autostart', True):
        #    self.start()

    def start(self, from_run=False):
        self._lock.acquire()
        if from_run or self._stopped:
            self._stopped = False
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self._lock.release()

    def _run(self):
        self.start(from_run=True)
        self.function(*self.args, **self.kwargs)

    def stop(self):
        self._lock.acquire()
        self._stopped = True
        self._timer.cancel()
        self._lock.release()


class Ads(object):

    def __init__(self, ads_cabinet,
                 campaign_id=None,
                 ads_obj_list=[],
                 ads_id_list=[],
                 ads_cost_type_list=[],
                 ads_data=[],
                 switch_log=[],
                 ads_clicks_array=[],
                 ads_impressions_array=[],
                 ads_winner_array=[],
                 ads_optimal_choice=-1):

        self.ads_cabinet = ads_cabinet
        self.ads_obj_list = ads_obj_list
        self.ads_id_list = ads_id_list
        self.ads_cost_type_list = ads_cost_type_list
        self.campaign_id = campaign_id
        self.ads_data = ads_data
        self.switch_log = switch_log
        self.ads_clicks_array = ads_clicks_array
        self.ads_impressions_array = ads_impressions_array
        self.ads_winner_array = ads_winner_array
        self.ads_optimal_choice = ads_optimal_choice

    def __len__(self):
        return len(self.ads_obj_list)

    def load(self, campaign_id):
        """Initial procedures: get ads list, fetch data, load ads first time, update ads stats, fill arrays"""
        self.campaign_id = campaign_id
        self._clear_ads()
        self._get_ads_list()
        self._fetch_data()
        self._load_ads()
        self._update_ads()
        self._fill_ads_click_impr_array()
        self._fill_winner_array()

    def update(self):
        """Update ads data: fetch data, update ads, fill ads click impressions, fill winner array."""
        self._fetch_data()
        self._update_ads()
        self._fill_ads_click_impr_array()
        self._fill_winner_array()


    def _clear_ads(self):
        """Reset all parametrs to defaults."""
        self.ads_obj_list = []
        self.ads_id_list = []
        self.ads_data = []
        self.switch_log = []
        self.ads_clicks_array = []
        self.ads_impressions_array = []
        self.ads_optimal_choice = -1

    def _get_ads_list(self):
        """Get all ads ids from current ads campaign."""
        session = vk.Session()
        api = vk.API(session, v=self.ads_cabinet.api_ver)
        time.sleep(1)
        result = api.ads.getAds(access_token=self.ads_cabinet.vk_api,
                                account_id=self.ads_cabinet.cabinet_id,
                                campaign_ids=f'{{"account_id":{self.campaign_id}}}')
        result_list = []
        result_cost_type_list = []
        for ad in result:
            result_list.append({ad["id"]: ad["name"]})
            result_cost_type_list.append({ad["id"]: ad["cost_type"]})
        self.ads_id_list = result_list
        self.ads_cost_type_list = result_cost_type_list

    def _fetch_data(self):
        """Load statistics from VK via API, saves to self.ads_data."""
        session = vk.Session()
        api = vk.API(session, v=self.ads_cabinet.api_ver)

        ids_list = []
        for ad in self.ads_id_list:
            for key, value in ad.items():
                ids_list.append(key)
        ids_string = ",".join(ids_list)
        time.sleep(1)
        result = api.ads.getStatistics(access_token=self.ads_cabinet.vk_api,
                                       account_id=self.ads_cabinet.cabinet_id,
                                       ids_type='ad',
                                       ids=ids_string,
                                       period='overall',
                                       date_from='overall: 0',
                                       date_to='overall: 0')
        self.ads_data = result

    def _load_ads(self):
        """Creates Ad objects form ads_data and loads into ads_obj_set."""
        ads_id_name_dic = {}
        for ad in self.ads_id_list:
            ads_id_name_dic.update(ad)

        ads_cost_type_dic = {}
        for ad in self.ads_cost_type_list:
            ads_cost_type_dic.update(ad)

        for ad_dic in self.ads_data:
            ad_id = ad_dic["id"]
            ad_name = ads_id_name_dic[str(ad_id)]
            ad_cost_type = ads_cost_type_dic[str(ad_id)]
            ad = Ad(ad_id, ad_name, self.ads_cabinet, ad_cost_type)
            self._insert_ad(ad)

    def _update_ads(self):
        """Update Ad objects from ads_date."""
        for ad in self.ads_obj_list:
            for data in self.ads_data:
                if data["id"] == ad.ad_id:
                    if ('stats' in data) and (data['stats']):
                        if 'impressions' in data['stats'][0]:
                            ad.set_stats(impressions=data['stats'][0]['impressions'])
                        if 'clicks' in data['stats'][0]:
                            ad.set_stats(clicks=data['stats'][0]['clicks'])
        self._update_ads_status()
        self._remove_rejected_ads()

    def _update_ads_status(self):
        """Update ads run and approvement status. 0 - stopped, 1 - running."""
        session = vk.Session()
        api = vk.API(session, v=self.ads_cabinet.api_ver)
        time.sleep(1)
        result = api.ads.getAds(access_token=self.ads_cabinet.vk_api,
                                account_id=self.ads_cabinet.cabinet_id,
                                campaign_ids=f'{{"account_id":{self.campaign_id}}}')

        for ad in self.ads_obj_list:
            for data in result:
                if data["id"] == str(ad.ad_id):
                    if 'status' in data:
                        ad.run_status = int(data['status'])
                    if 'approved' in data:
                        ad.approved = int(data['approved'])

    def _insert_ad(self, ad_obj):
        """Insert ad object into testing Ads set."""
        self.ads_obj_list.append(ad_obj)

    def _remove_rejected_ads(self):
        """Exclude rejected ads from ads object list."""
        for ad in self.ads_obj_list:
            if ad.approved == 3:
                self.ads_obj_list.remove(ad)

    def _fill_ads_click_impr_array(self):
        """Fill ads click and impressions array from Ad objects."""
        ads_len = len(self.ads_obj_list)
        self.ads_clicks_array = np.zeros(ads_len)
        self.ads_impressions_array = np.zeros(ads_len)

        for i in range(len(self.ads_obj_list)):
            self.ads_clicks_array[i] = self.ads_obj_list[i].clicks
            self.ads_impressions_array[i] = self.ads_obj_list[i].impressions

    def _fill_winner_array(self):
        """Fill winner array from ads data"""
        self.ads_winner_array = []
        list = []
        for ad in self.ads_obj_list:
            ad.count_posterior()
            list.append(ad.posterior_samples)

        samples = len(list[0])
        best_array = np.zeros(samples)
        ads_number = len(list)
        for i in range(samples):
            temp_arr = np.zeros(ads_number)
            for k in range(ads_number):
                temp_arr[k] = list[k][i]
            best_array[i] = temp_arr.argmax()
        for j in range(ads_number):
            self.ads_winner_array.append("{:.2%}".format((best_array == j).mean()))

    def show_image(self):
        """Show image of probabilities"""
        X = np.linspace(0, 0.049, 5000)
        for i in range(len(self.ads_obj_list)):
            Y = beta.pdf(X, 1 + self.ads_clicks_array[i], 1 + self.ads_impressions_array[i] - self.ads_clicks_array[i])
            plt.plot(X, Y, label=str(self.ads_obj_list[i].ad_name))
            plt.legend(loc='upper right')
        plt.show()

    def get_summary(self):
        """Provides information for Ads List View in list of tuples format (human_name, some identifier)"""
        return_tuple_list = []
        if self.ads_obj_list:
            for index, ad in enumerate(self.ads_obj_list):
                data_list = []
                name = ad.ad_name
                if (self.ads_optimal_choice >= 0) and (self.ads_optimal_choice == index):
                    name = ">" + name
                clicks = str(ad.clicks)
                impressions = str(ad.impressions)
                ctr = ad.get_ctr()
                win = self.ads_winner_array[index]
                return_tuple_list.append(([name, clicks, impressions, ctr, win], ad.ad_id))
        return return_tuple_list


class Ad(object):

    def __init__(self, ad_id, ad_name, cabinet, cost_type, impressions=0,
                 clicks=0, run_status=0, approved=0, posterior_samples=None):
        self.ad_id = ad_id
        self.ad_name = ad_name
        self.cabinet = cabinet
        self.cost_type = cost_type
        self.impressions = impressions
        self.clicks = clicks
        self.run_status = run_status
        self.approved = approved
        self.posterior_samples = posterior_samples

    def start_ad(self):
        """Start ad by command via VK API"""
        session = vk.Session()
        api = vk.API(session, v=self.cabinet.api_ver)
        result = api.ads.updateAds(access_token=self.cabinet.vk_api,
                                   account_id=self.cabinet.cabinet_id,
                                   data=f'[{{"ad_id":{self.ad_id}, "status":1}}]')
        self.run_status = 1
        return result

    def stop_ad(self):
        """Stop ad by command via VK API"""
        session = vk.Session()
        api = vk.API(session, v=self.cabinet.api_ver)
        result = api.ads.updateAds(access_token=self.cabinet.vk_api,
                                   account_id=self.cabinet.cabinet_id,
                                   data=f'[{{"ad_id":{self.ad_id}, "status":0}}]')
        self.run_status = 0
        return result

    def set_stats(self, impressions=None, clicks=None):
        """Set statistics for an ad"""
        if impressions:
            self.impressions = impressions
        if clicks:
            self.clicks = clicks

    def get_ctr(self, probability=0.95):
        """Returns CTR period with given probability."""
        ad_posterior = beta(1 + self.clicks, 1 + self.impressions - self.clicks)
        return "{:.2%}—{:.2%}".format(*ad_posterior.interval(probability))

    def count_posterior(self, samples=10000):
        """Count posterior samples from current click and impressions, saves to self.posterior_samples."""
        posterior = beta(1 + self.clicks, 1 + self.impressions - self.clicks)
        self.posterior_samples = posterior.rvs(samples)


class BidManager(object):
    """Bids class to store information and behaviour about bids."""
    def __init__(self, max_bid=-1,
                 min_bid=-1,
                 bid_points=[],
                 history=[],
                 current_bid_index=-1,
                 current_time=-1):
        self.max_bid = max_bid
        self.min_bid = min_bid
        self.bid_points = bid_points
        self.history = history
        self.current_bid_index = current_bid_index
        self.current_time = current_time


    def start(self):
        """Start working. Generate bids from max, all numbers in penny"""
        def make_points(max_bid, min_bid):
            bid_points = [0] * 9
            bid_points[0] = min_bid
            bid_points[8] = max_bid
            bid_points[4] = ((max_bid - min_bid) // 2) + min_bid
            bid_points[2] = ((bid_points[4] - bid_points[0]) // 2) + bid_points[0]
            bid_points[6] = ((bid_points[8] - bid_points[4]) // 2) + bid_points[4]
            bid_points[1] = ((bid_points[2] - bid_points[0]) // 2) + bid_points[0]
            bid_points[3] = ((bid_points[4] - bid_points[2]) // 2) + bid_points[2]
            bid_points[5] = ((bid_points[6] - bid_points[4]) // 2) + bid_points[4]
            bid_points[7] = ((bid_points[8] - bid_points[6]) // 2) + bid_points[6]
            return bid_points

        if (self.max_bid >= 30_00) and (self.max_bid <= 1000_00):
            self.min_bid = 30_00
            self.bid_points = make_points(self.max_bid, self.min_bid)
            self.current_time = 0
            self.current_bid_index = self.choose_bid()
            return self.bid_points[self.current_bid_index]
        elif (self.max_bid >= 1_20) and (self.max_bid <= 20_00):
            self.min_bid = 1_20
            self.bid_points = make_points(self.max_bid, self.min_bid)
            self.current_time = 0
            self.current_bid_index = self.choose_bid()
            return self.bid_points[self.current_bid_index]
        else:
            print("Start error")
            return False

    def update(self, ad_id, ad_impressions):
        """Get statistics for current ad."""
        snap = {"ad_id": ad_id, "bid_index": self.current_bid_index, "ad_impressions": ad_impressions}
        self.history.append(snap)
        self.history[self.current_time].update(self.count_reward())
        self.current_time += 1
        self.current_bid_index = self.choose_bid()
        return self.bid_points[self.current_bid_index]

    def count_reward(self):

        def previous_impressions(ad_id):
            for snap in reversed(range(self.current_bid_index)):
                if snap["ad_id"] == ad_id:
                    return snap["ad_impressions"]
            return 0

        delta_impressions = self.history[self.current_time]["ad_impressions"] -\
                            previous_impressions(self.history[self.current_time]["ad_id"])

        reward = float(delta_impressions / self.bid_points[self.current_bid_index])
        return {"reward": reward}



    def choose_bid(self):
        """Not real algo still, just for testing"""
        import random
        random_choice = random.choice([0,1,2,3,4,5,6,7,8])
        return random_choice


class Cabinet(object):

    def __init__(self, cabinet_id=None,
                 vk_api=None,
                 api_ver=5.101,
                 accounts_data=None,
                 client_id=None,
                 ads_campaigns_data=None,
                 cabinet_choice=None,
                 campaign_choice=None):

        self.cabinet_id = cabinet_id
        self.vk_api = vk_api
        self.api_ver = api_ver
        self.accounts_data = accounts_data
        self.client_id = client_id
        self.ads_campaigns_data = ads_campaigns_data
        self.cabinet_choice = cabinet_choice
        self.campaign_choice = campaign_choice

        # Get ads campaign data when created
        self._load_api_key()
        if self.vk_api:
            self._get_accounts_data()

    def _load_api_key(self):
        """Load api key from settings file and save to self.vk_api. If not existing - create one."""
        if self._if_settings_exist():
            with open('settings', 'r') as file:
                api_key = "".join(file.readlines())
                self.vk_api = api_key
        else:
            with open('settings', 'w+') as file:
                file.write('')

    def _if_settings_exist(self):
        """Check if setting file exists. Returns True of False."""
        try:
            f = open('settings')
            f.close()
        except IOError:
            return False
        return True

    def _save_api_key(self):
        """Saves api key to file 'settings'"""
        with open('settings', 'w+') as file:
            file.write(self.vk_api)

    def _get_accounts_data(self):
        """Get list of accounts from current API token."""
        session = vk.Session()
        api = vk.API(session, v=self.api_ver)
        result = api.ads.getAccounts(access_token=self.vk_api)
        self.accounts_data = result

    def load(self, cabinet_id):
        """Load ads campaign data from given cabinet by id."""
        self.cabinet_id = cabinet_id
        self._get_ads_campaigns_data(cabinet_id)

    def _get_ads_campaigns_data(self, account_id):
        """Get ads campaigns data from current cabinet. Returns campaigns data """
        session = vk.Session()
        api = vk.API(session, v=self.api_ver)
        result = api.ads.getCampaigns(access_token=self.vk_api,
                                      account_id=account_id,
                                      include_deleted=0,
                                      campaign_ids='null',
                                      client_id=self.client_id)
        self.ads_campaigns_data = result

    def get_campaigns(self):
        """Get ads campaign list from ads_campaigns_data. Return list of tuples."""
        return_tuple_list = []
        if self.ads_campaigns_data:
            for campaign in self.ads_campaigns_data:
                data_list = []
                name = campaign["name"]
                return_tuple_list.append(([name], campaign['id']))
        return return_tuple_list

    def get_accounts(self):
        """Provides information of accounts for API key in list of tuples format (human_name, some identifier)"""
        return_tuple_list = []
        if self.accounts_data:
            for account in self.accounts_data:
                data_list = []
                name = account["account_name"]
                return_tuple_list.append(([name], account['account_id']))
        return return_tuple_list


class Robot(object):

    def __init__(self, cabinet, ads, timer, working_flag=False):
        self.cabinet = cabinet
        self.ads = ads
        self.timer = timer
        self.timer.interval = 300 #seconds
        self.timer.function = self.make_decision
        self.working_flag = working_flag

    def start_experiment(self):
        """Start experiment for given ads campaign."""
        self.working_flag = True
        self.make_decision()
        self.timer.start()

    def stop_experiment(self):
        """Stop experiment for given ads campaign."""
        self.working_flag = False
        self.timer.stop()
        for ad in self.ads.ads_obj_list:
            if ad.run_status == 1:
                ad.stop_ad()

    def log(self, text):
        """Logging function."""
        pass

    def make_decision(self):
        """Robot makes decision what ads to run next N minutes."""
        self.ads.update()
        b = rbeta(1 + self.ads.ads_clicks_array, 1 + self.ads.ads_impressions_array - self.ads.ads_clicks_array)
        new_optimal_choice = np.argmax(b)

        if self.choice_changed(new_optimal_choice):
            self.ads.ads_optimal_choice = new_optimal_choice
            self.ads.ads_obj_list[new_optimal_choice].start_ad()
            self.stop_other_ads(new_optimal_choice)
        else:
            self.ads.ads_obj_list[new_optimal_choice].start_ad()
            self.log("Choice not changed")

    def choice_changed(self, number):
        '''Check if choice for testing has changed. Returns true of false'''
        return number != self.ads.ads_optimal_choice

    def stop_other_ads(self, number):
        """Stop all other ads, excluding ads with ad[number]"""
        for i in range(len(self.ads)):
            if (i != number) and (self.ads.ads_obj_list[i].run_status == 1):
                self.ads.ads_obj_list[i].stop_ad()


class ListView(Frame):

    def __init__(self, screen, ads, robot):
        super(ListView, self).__init__(screen,
                                       screen.height,
                                       screen.width,
                                       on_load=self._reload_list,
                                       hover_focus=True,
                                       can_scroll=False,
                                       title="Список объявлений")

        self._ads = ads
        self._robot = robot
        self.set_theme("green")

        self._ads_list_view = MultiColumnListBox(
            Widget.FILL_FRAME,
            columns=[25,10,10,15,10],
            options=ads.get_summary(),
            name="ads",
            titles=["Название", "Клики", "Показы", "CTR(шанс 95%)", "Ротация"],
            add_scroll_bar=True,
            on_change=self._on_pick,
            on_select=self._ad_selected)

        self._start_button = Button("Старт", self._start)
        self._stop_button = Button("Стоп", self._stop)
        self._image_button = Button("График", self._show_image)
        self._refresh_button = Button("Обновить", self._reload_list)
        self._setup_button = Button("Настройки", self._setup)
        layout = Layout([100], fill_frame=True)
        self.add_layout(layout)
        layout.add_widget(self._ads_list_view)

        layout.add_widget(Divider())

        layout2 = Layout([1, 1, 1, 1, 1, 1])
        self.add_layout(layout2)
        layout2.add_widget(self._start_button, 0)
        layout2.add_widget(self._stop_button, 1)
        layout2.add_widget(self._image_button, 2)
        layout2.add_widget(self._refresh_button, 3)
        layout2.add_widget(self._setup_button, 4)
        layout2.add_widget(Button("Выход", self._quit), 5)
        self.fix()
        self._on_pick()

    def _on_pick(self):
        self._image_button.disabled = self._ads_list_view.value is None
        self._stop_button.disabled = self._robot.working_flag is False
        self._start_button.disabled = (self._ads_list_view.value is None) or (self._robot.working_flag is True)


    def _ad_selected(self):
        ad_id = self._ads_list_view.value
        url = "https://vk.com/ads?act=office&union_id={}".format(ad_id)
        webbrowser.open_new_tab(url)

    def _reload_list(self, new_value=None):
        self._ads_list_view.options = self._ads.get_summary()
        self._ads_list_view.value = new_value

    def _start(self):
        if not self._robot.working_flag:
            self._robot.start_experiment()
            self._start_button.disabled = True
            self._stop_button.disabled = False

    def _stop(self):
        if self._robot.working_flag:
            self._robot.stop_experiment()
            self._stop_button.disabled = True
            self._start_button.disabled = False

    def _show_image(self):
        self._ads.show_image()

    def _setup(self):
        raise NextScene("Setup")

    @staticmethod
    def _quit():
        raise StopApplication("User pressed quit")


class SetupView(Frame):

    def __init__(self, screen, cabinet, ads):
        super(SetupView, self).__init__(screen,
                                       screen.height,
                                       screen.width,
                                       on_load=self._reload_account_list,
                                       hover_focus=True,
                                       can_scroll=False,
                                       title="Выбор кампании")
        self._cabinet = cabinet
        self._ads = ads
        self.set_theme("green")

        self._account_list_view = MultiColumnListBox(
            Widget.FILL_FRAME,
            columns=[100],
            options=cabinet.get_accounts(),
            name="accounts",
            titles=["Аккаунт",],
            add_scroll_bar=True,
            on_change=self._on_account_pick,
            on_select=self._account_selected)

        self._campaign_list_view = MultiColumnListBox(
            Widget.FILL_FRAME,
            columns=[100],
            options=cabinet.get_campaigns(),
            name="campaign",
            titles=["Кампания",],
            add_scroll_bar=True,
            on_change=self._on_campaign_pick,
            on_select=self._campaign_selected)

        layout = Layout([25,1,25], fill_frame=True)
        self.add_layout(layout)
        layout.add_widget(self._account_list_view, 0)
        layout.add_widget(VerticalDivider(),1)
        layout.add_widget(self._campaign_list_view, 2)

        layout.add_widget(Divider(), 0)
        layout.add_widget(Divider(), 1)
        layout.add_widget(Divider(), 2)

        layout2 = Layout([1, 1, 1, 1])
        self.add_layout(layout2)
        layout2.add_widget(Button("Настройки токена", self._settings), 0)
        layout2.add_widget(Button("Отмена", self._cancel), 3)
        self.fix()

    def _reload_account_list(self, new_value=None):
        self._account_list_view.options = self._cabinet.get_accounts()
        self._account_list_view.value = new_value

    def _reload_campaign_list(self, new_value=None):
        self._campaign_list_view.options = self._cabinet.get_campaigns()
        self._campaign_list_view.value = new_value

    def _on_account_pick(self):
        self._cabinet.account_choice = self._account_list_view.value

    def _on_campaign_pick(self):
        self._cabinet.campaign_choice = self._campaign_list_view.value

    def _account_selected(self):
        self._cabinet._get_ads_campaigns_data(account_id=self._account_list_view.value)
        self._campaign_list_view.options = self._cabinet.get_campaigns()
        self._cabinet.cabinet_choice = self._account_list_view.value

    def _campaign_selected(self):
        self._cabinet.campaign_choice = self._campaign_list_view.value
        self._ok()

    def _ok(self):
        self._cabinet.cabinet_id = self._cabinet.cabinet_choice
        self._ads.load(str(self._cabinet.campaign_choice))
        raise NextScene("Main")

    def _settings(self):
        raise NextScene("Settings")

    @staticmethod
    def _cancel():
        raise NextScene("Main")


class SettingsView(Frame):

    def __init__(self, screen):
        super(SettingsView, self).__init__(screen,
                                        screen.height,
                                        screen.width * 2 // 3,
                                        hover_focus=True,
                                        can_scroll=False,
                                        title="Настройки токена",
                                        reduce_cpu=True)
        self.set_theme("green")

        self._register_button = Button("1.Регистрация приложения", self._register_app)
        self._get_token_button = Button("2.Получение токена", self._get_token)
        self._set_token_button = Button("3.Введение токена", self._set_token)
        self._manual_button = Button("Инструкция по установке", self._manual)
        self._video_button = Button("Видео инструкция", self._video)

        layout = Layout([100], fill_frame=True)
        self.add_layout(layout)
        layout.add_widget(self._register_button)
        layout.add_widget(self._get_token_button)
        layout.add_widget(self._set_token_button)
        layout.add_widget(self._manual_button)
        layout.add_widget(self._video_button)
        layout.add_widget(Divider())

        layout2 = Layout([100])
        self.add_layout(layout2)
        layout2.add_widget(Button("Назад", self._back))
        self.fix()

    def _register_app(self):
        url = "https://vk.com/editapp?act=create"
        webbrowser.open_new_tab(url)

    def _get_token(self):
        raise NextScene("Token")

    def _set_token(self):
        raise NextScene("SetToken")

    def _manual(self):
        raise NextScene("Manual")

    def _video(self):
        url = "https://www.youtube.com/watch?v=Xyqud4nFRrQ"
        webbrowser.open_new_tab(url)

    def _back(self):
        raise NextScene("Setup")


class TokenView(Frame):

    def __init__(self, screen, cabinet):
        super(TokenView, self).__init__(screen,
                                        screen.height * 2 // 3,
                                        screen.width * 2 // 3,
                                        hover_focus=True,
                                        can_scroll=False,
                                        title="Получение токена",
                                        reduce_cpu=True)
        self._cabinet = cabinet
        self.set_theme("green")

        layout = Layout([100], fill_frame=True)
        self.add_layout(layout)
        layout.add_widget(Text("ID приложения:", "ad_id", max_length=20))
        layout.add_widget(Divider())

        layout2 = Layout([1, 1, 1, 1])
        self.add_layout(layout2)
        layout2.add_widget(Button("Получить", self._get_token), 0)
        layout2.add_widget(Button("Назад", self._back), 3)
        self.fix()

    def reset(self):
        super(TokenView, self).reset()

    def _get_token(self):
        self.save()
        url = (
            'https://oauth.vk.com/authorize?'
            'client_id={}&display=page&'
            'redirect_uri=https://oauth.vk.com/blank.html'
            '&scope=ads,offline&response_type=token&v={}'.format(self.data["ad_id"], self._cabinet.api_ver)
        )
        webbrowser.open_new_tab(url)
        raise NextScene("SetToken")

    def _back(self):
        raise NextScene("Settings")


class SetTokenView(Frame):

    def __init__(self, screen, cabinet):
        super(SetTokenView, self).__init__(screen,
                                        screen.height * 2 // 3,
                                        screen.width * 2 // 3,
                                        hover_focus=True,
                                        can_scroll=False,
                                        title="Введение токена",
                                        reduce_cpu=True)
        self._cabinet = cabinet
        self.set_theme("green")

        layout = Layout([100], fill_frame=True)
        self.add_layout(layout)
        layout.add_widget(Text("Ваш токен:", "token"))
        layout.add_widget(Divider())

        layout2 = Layout([1, 1, 1, 1])
        self.add_layout(layout2)
        layout2.add_widget(Button("Сохранить", self._setup_token), 0)
        layout2.add_widget(Button("Назад", self._back), 3)
        self.fix()

    def reset(self):
        super(SetTokenView, self).reset()

    def _setup_token(self):
        self.save()
        self._cabinet.vk_api = self.data["token"]
        self._cabinet._save_api_key()
        self._cabinet._get_accounts_data()
        raise NextScene("Setup")

    def _back(self):
        raise NextScene("Settings")


class ManualView(Frame):

    def __init__(self, screen):
        super(ManualView, self).__init__(screen,
                                        screen.height,
                                        screen.width * 2 // 3,
                                        hover_focus=True,
                                        can_scroll=False,
                                        title="Инструкция по установке",
                                        reduce_cpu=True)
        self.set_theme("green")

        self._manual_text = TextBox(Widget.FILL_FRAME, "", "notes", as_string=True, line_wrap=True)

        layout = Layout([100], fill_frame=True)
        self.add_layout(layout)
        layout.add_widget(self._manual_text)
        layout.add_widget(Divider())

        layout2 = Layout([100])
        self.add_layout(layout2)
        layout2.add_widget(Button("Назад", self._back))
        self.fix()

    def reset(self):
        # Do standard reset to clear out form, then populate with new data.
        super(ManualView, self).reset()
        self.data = {"notes": text_manual}

    def _back(self):
        raise NextScene("Settings")


#Initialization of main classes
c = Cabinet(); a = Ads(c); t = PeriodicTimer(); r = Robot(c,a,t)

def demo(screen, scene):
    #Start Text User Interface
    scenes = []

    effects = [
        Mirage(
            screen,
            FigletText("Target Bandit"),
            screen.height // 2 - 3,
            Screen.COLOUR_GREEN,
            start_frame=0,
            stop_frame=75),
    ]

    scenes = [
        Scene(effects, 75, clear=False),
        Scene([ListView(screen, a, r)], -1, name="Main"),
        Scene([SetupView(screen, c, a)], -1, name="Setup"),
        Scene([TokenView(screen, c)], -1, name="Token"),
        Scene([SetTokenView(screen, c)], -1, name="SetToken"),
        Scene([SettingsView(screen)], -1, name="Settings"),
        Scene([ManualView(screen)], -1, name="Manual"),
    ]
    screen.play(scenes, stop_on_resize=True, start_scene=scene, allow_int=True)

last_scene = None
text_manual = """При первом запуске программы TargetBandit нужно пройти несколько этапов настройки: создать приложение, получить к нему токен, ввести токен в программу. В дальнейшей работе токен будет загружаться автоматически.

1. Создание приложения. В разделе «Настройки токена» кликните на кнопке «Регистрация приложения», сайт ВКонтакте откроется  в новой вкладке браузера. Введите название приложения (например, TargetBandit), выберите платформу «Standalone-приложение», нажмите кнопку «Подключить приложение». Войдите в раздел «Настройки» и выставите «Состояние» в значение «Приложение включено и доступно всем». Скопируйте в буфер (Ctrl+C) или запишите номер «ID приложения». Нажмите кнопку «Сохранить изменения».

2. Получение токена. Вернитесь в окно программы «TargetBandit» и введите «ID приложения» из предыдущего пункта или вставьте его из буфера (в Windows: Alt+Space - Изменить - Вставить). Нажмите кнопку «Получить». В браузере откроется новая вкладка с запросом доступа к вашему аккаунту ранее созданного прилжения. Нажмите «Разрешить». В адресной строке браузера дважды кликните на число-буквенный код после «...access_token=» и скопируйте его в буфер (Ctrl+C). ВНИМАНИЕ: не передавайте токен третьим лицам, это ключи от вашего рекламного кабинета!

3. Введение токена. Вернитесь в окно пограммы «Target Bandit» в графе «Ваш токен» вставьте из буфера токен (в Windows: Alt+Space - Изменить - Вставить). Нажмите «Сохранить». В случае успеха вам отобразится список аккаунтов.

4. Если список аккаунтов не отобразился. Во-первых, проверьте создано и включено ли standalone-приложение. Во-вторых, попробуйте еще раз получить токен на ID вашего приложения. В-третьих, проверьте правильно ли вы скопировали токен из адресной строки. Это число-буквенный код между «...access_token=» и «&expires_in=». Токен должен содержать только числа и буквы.

5. Ваш токен хранится в открытом виде в файле settings в корневом каталоге приложения. При удалении данного файла настройки программы скидываются."""

while True:
    try:
        Screen.wrapper(demo, catch_interrupt=True, arguments=[last_scene])
        sys.exit(0)
    except ResizeScreenError as e:
        last_scene = e.scene