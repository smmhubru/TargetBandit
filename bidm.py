class BidManager(object):
    """Bids class to store information and behaviour about bids."""
    def __init__(self, max_bid=-1,
                 min_bid=-1,
                 bid_points=[],
                 history=[],
                 current_bid_index=-1,
                 current_time=-1,
                 working_flag=False):
        self.max_bid = max_bid
        self.min_bid = min_bid
        self.bid_points = bid_points
        self.history = history
        self.current_bid_index = current_bid_index
        self.current_time = current_time
        self.working_flag = working_flag

    def start(self, max_bid):
        self.max_bid = max_bid
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
            self.current_bid_index = self._choose_bid()
            self.working_flag = True
            return self.bid_points[self.current_bid_index]
        elif (self.max_bid >= 1_20) and (self.max_bid <= 20_00):
            self.min_bid = 1_20
            self.bid_points = make_points(self.max_bid, self.min_bid)
            self.current_time = 0
            self.current_bid_index = self._choose_bid()
            self.working_flag = True
            return self.bid_points[self.current_bid_index]
        else:
            print("Start error")
            return False

    def stop(self):
        """Stop working, clear history"""
        self.working_flag = False
        self.max_bid = -1
        self.min_bid = -1
        self.bid_points = []
        self.history = []
        self.current_bid_index = -1
        self.current_time = -1

    def update(self, ad_id, ad_impressions):
        """Update previous history in case of additional impressions on stopped ad."""
        if self.current_time > 0:
            for i in reversed(range(self.current_time)):
                if self.history[i]["ad_id"] == ad_id:
                    if self.history[i]["total_impressions"] < ad_impressions:
                        delta = ad_impressions - self.history[i]["total_impressions"]
                        self.history[i]["total_impressions"] = ad_impressions
                        self.history[i]["round_impressions"] += delta
                        self.history[i]["reward"] = float(self.history[i]["round_impressions"] /
                                                          self.bid_points[self.history[i]["bid_index"]])
                        return True
                    else:
                        return False
            return False

    def commit(self, ad_id, ad_impressions):
        """Get statistics for current ad."""
        if self.working_flag:
            snap = {"ad_id": ad_id, "bid_index": self.current_bid_index, "total_impressions": ad_impressions}
            self.history.append(snap)
            self.history[self.current_time].update(self._round_impressions())
            self.history[self.current_time].update(self._round_reward())
            self.current_time += 1
            self.current_bid_index = self._choose_bid()
            return self.bid_points[self.current_bid_index]

    def _previous_impressions(self, ad_id):
        if self.current_time > 0:
            for i in reversed(range(self.current_time)):
                if self.history[i]["ad_id"] == ad_id:
                    return self.history[i]["total_impressions"]
            return 0
        else:
            return 0

    def _round_impressions(self):
        delta_impressions = self.history[self.current_time]["total_impressions"] - \
                            self._previous_impressions(self.history[self.current_time]["ad_id"])
        return {"round_impressions": delta_impressions}

    def _round_reward(self):
        round_impressions = self.history[self.current_time]["round_impressions"]
        reward = float(round_impressions / self.bid_points[self.current_bid_index])
        return {"reward": reward}

    def _choose_bid(self):
        """Not real algo still, just for testing"""
        import random
        random_choice = random.choice([0,1,2,3,4,5,6,7,8])
        return random_choice

bm = BidManager()
bm.start(200_00)