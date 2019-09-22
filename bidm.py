class BidManager(object):
    """Bids class to store information and behaviour about bids."""
    def __init__(self, max_bid=-1,
                 min_bid=-1,
                 bid_points=[],
                 history=[],
                 current_bid_index=-1,
                 current_time=-1,
                 working_flag=False,
                 bid_rewards=[],
                 run_counts=[],
                 bid_values=[],
                 temperature=0.0003,
                 bid_probabilities=[]):
        self.max_bid = max_bid
        self.min_bid = min_bid
        self.bid_points = bid_points
        self.history = history
        self.current_bid_index = current_bid_index
        self.current_time = current_time
        self.working_flag = working_flag
        self.bid_rewards = bid_rewards
        self.run_counts = run_counts
        self.bid_values = bid_values
        self.temperature = temperature
        self.bid_probabilities = bid_probabilities

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

        self.bid_rewards = [0.0] * 9
        self.run_counts = [0] * 9
        self.bid_values = [0.0] * 9

        if (self.max_bid >= 30_00) and (self.max_bid <= 1000_00):
            self.min_bid = 30_00
            self.bid_points = make_points(self.max_bid, self.min_bid)
            self.current_time = 0
            self.current_bid_index = self._choose_bid_ucb()
            self.working_flag = True
            return self.bid_points[self.current_bid_index]
        elif (self.max_bid >= 1_20) and (self.max_bid <= 20_00):
            self.min_bid = 1_20
            self.bid_points = make_points(self.max_bid, self.min_bid)
            self.current_time = 0
            self.current_bid_index = self._choose_bid_ucb()
            self.working_flag = True
            return self.bid_points[self.current_bid_index]
        else:
            print("Start error")
            return False

    def stop(self):
        """Stop working, clear history"""
        if self.working_flag:
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
                        self.bid_rewards[self.history[i]["bid_index"]] -= self.history[i]["reward"]
                        self.history[i]["reward"] = float(self.history[i]["round_impressions"] /
                                                          self.bid_points[self.history[i]["bid_index"]])
                        self.bid_rewards[self.history[i]["bid_index"]] += self.history[i]["reward"]
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
            reward = self._round_reward()
            self.history[self.current_time].update(reward)
            self.current_time += 1
            self.run_counts[self.current_bid_index] += 1
            self._update_values(self.current_bid_index, reward["reward"])
            self.bid_rewards[self.current_bid_index] += reward["reward"]
            self.current_bid_index = self._choose_bid_ucb() #change algo here
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

    def _update_values(self, choosen_bid_index, reward):
        n = self.run_counts[choosen_bid_index]
        value = self.bid_values[choosen_bid_index]
        new_value = ((n - 1) / float(n)) * value + (1 / float(n)) * reward
        self.bid_values[choosen_bid_index] = new_value

    def _choose_bid(self):
        """Softmax algo working with temperature."""
        import random
        import math
        z = sum([math.exp(v / self.temperature) for v in self.bid_values])
        probabilites = [math.exp(v / self.temperature) / z for v in self.bid_values]
        self.bid_probabilities = probabilites

        r = random.random()
        cummulative_probablities = 0.0
        for i in range(len(probabilites)):
            prob = probabilites[i]
            cummulative_probablities += prob
            if cummulative_probablities > r:
                return i
        return len(probabilites) - 1

    def _choose_bid_ucb(self):
        """UCB1 working algo"""
        import math
        n_arms = len(self.bid_points)
        for arm in range(n_arms):
            if self.run_counts[arm] == 0:
                print("прогрев")
                return arm

        ucb_values = [0.0] * n_arms
        total_counts = sum(self.run_counts)

        for arm in range(n_arms):
            bonus = ((math.log(total_counts) / 500000) / float(self.run_counts[arm])) ** (1./2)
            print(bonus)
            ucb_values[arm] = self.bid_values[arm] + bonus
        print(ucb_values)
        choice = self._ind_max(ucb_values)
        print(choice)
        return choice

    def _ind_max(self, x):
        m = max(x)
        return x.index(m)


class BidArm(object):
    def __init__(self, recommended_bid=300_00,
                 temp=0.8,
                 base_size=5000):
        self.recommended_bid = recommended_bid
        self.temp = temp
        self.base_size = base_size

    def _prob(self, x):
        if (x < 30_00) or (x > 1000_00):
            return False
        if x >= self.recommended_bid:
            y = pow(x, float(1) / 3)
        elif x < self.recommended_bid:
            y = -pow(abs(x - self.recommended_bid), float(1) / 3) + pow(self.recommended_bid, float(1) / 3)
        result = self.temp * (y / (pow(self.recommended_bid, float(1) / 3)))
        if result > 1:
            return 1
        else:
            return result

    def pull(self, bid):
        import random
        probability = self._prob(bid)
        result = 0
        for i in range(self.base_size // 200):
            if random.random() < probability:
                result += 1
        return result


bm = BidManager()
ba = BidArm()
imp_count = 0
start_bid = bm.start(400_00)
start_response = ba.pull(start_bid)
imp_count += start_response
response = bm.commit(1, imp_count)
for i in range(288):
    imp_count += ba.pull(response)
    response = bm.commit(1, imp_count)

