from datetime import datetime, timedelta
from core.Experiment import *


@behavior.schema
class Rewards(dj.Lookup):
    definition = """
    # reward types
    reward_type             : varchar(16)
    ---
    measurement_unit        : varchar(16) # unit of measurement for reward
    description             : varchar(256)
    """


@behavior.schema
class Punishments(dj.Lookup):
    definition = """
    # punishment types
    punishment_type         : varchar(16)
    ---
    measurement_unit        : varchar(16) # unit of measurement for reward
    description             : varchar(256)
    """


@behavior.schema
class BehCondition(dj.Manual):
    definition = """
    # reward probe conditions
    beh_hash               : char(24)                     # unique reward hash
    """

    class Trial(dj.Part):
        definition = """
        # movie clip conditions
        -> experiment.Trial
        -> BehCondition
        time			      : int 	                # time from session start (ms)
        """


@behavior.schema
class Ports(dj.Lookup):
    definition = """
    # Probe identity
    setup                    : varchar(256)                 # Setup name
    port                     : tinyint                      # port id
    conf_version             : tinyint                      # configuration version
    ---
    discription              : varchar(256)
    """


class PortCalibration(dj.Manual):
    definition = """
    # Liquid deliver y calibration sessions for each port with water availability
    -> Ports
    date                         : date                 # session date (only one per day is allowed)
    """

    class Liquid(dj.Part):
        definition = """
        # Data for volume per pulse duty cycle estimation
        -> PortCalibration
        pulse_dur                : int                  # duration of pulse in ms
        ---
        pulse_num                : int                  # number of pulses
        weight                   : float                # weight of total liquid released in gr
        timestamp                : timestamp            # timestamp
        """


class PortTest(dj.Part):
    definition = """
    # Lick timestamps
    -> Ports
    timestamp             : timestamp  
    ___
    result=null           : enum('Passed','Failed')
    pulses=null           : int
    """


class Behavior:
    """ This class handles the behavior variables """
    cond_tables = ['Reward']
    required_fields = ['reward_amount', 'port_id']
    default_key = {'reward_type': 'water', 'conf_version': 1}

    def setup(self, logger, params):
        self.params = params
        self.resp_timer = Timer()
        self.resp_timer.start()
        self.logger = logger
        self.rew_probe = 0
        self.choices = np.array(np.empty(0))
        self.choice_history = list()  # History term for bias calculation
        self.reward_history = list()  # History term for performance calculation
        self.licked_probe = 0
        self.reward_amount = dict()
        self.curr_cond = []

    def is_ready(self, init_duration, since=0):
        return True, 0

    def get_response(self, since=0):
        return False

    def get_cond_tables(self):
        return []

    def reward(self):
        return True

    def punish(self):
        pass

    def cleanup(self):
        pass

    def make_conditions(self, conditions):
        """generate and store stimulus condition hashes"""
        for cond in conditions:
            assert np.all([field in cond for field in self.required_fields])
            cond.update({**self.default_key, **cond, 'behavior_class': self.cond_tables[0]})
        return dict(conditions=conditions, condition_tables=['BehCondition'] + self.cond_tables,
                    schema='behavior', hsh='beh_hash')

    def prepare(self, condition):
        pass

    def update_history(self, choice=np.nan, reward=np.nan):
        self.choice_history.append(choice)
        self.reward_history.append(reward)
        self.logger.total_reward = np.nansum(self.reward_history)

    def get_false_history(self, h=10):
        idx = np.logical_and(np.isnan(self.reward_history), ~np.isnan(self.choice_history))
        return np.sum(np.cumprod(np.flip(idx[-h:])))

    def is_sleep_time(self):
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0) + self.logger.setup_info['start_time']
        stop = now.replace(hour=0, minute=0, second=0) + self.logger.setup_info['stop_time']
        if stop < start:
            stop = stop + timedelta(days=1)
        print(now, stop)
        time_restriction = now < start or now > stop
        return time_restriction

    def is_hydrated(self, rew=False):
        if rew:
            return self.logger.total_reward >= rew
        elif self.params['max_reward']:
            return self.logger.total_reward >= self.params['max_reward']
        else:
            return False





