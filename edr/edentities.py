import os
import json

import edtime
import edrlog
import edrconfig
from edri18n import _, _c
EDRLOG = edrlog.EDRLog()

class EDBounty(object):
    def __init__(self, value):
        self.value = value
        config = edrconfig.EDRConfig()
        self.threshold = config.intel_bounty_threshold()
    
    def is_significant(self):
        return self.value >= self.threshold

    def pretty_print(self):
        readable = ""
        if self.value >= 10000000000:
            # Translators: this is a short representation for a bounty >= 10 000 000 000 credits (b stands for billion)  
            readable = _(u"{} b").format(self.value / 1000000000)
        elif self.value >= 1000000000:
            # Translators: this is a short representation for a bounty >= 1 000 000 000 credits (b stands for billion)
            readable = _(u"{:.1f} b").format(self.value / 1000000000.0)
        elif self.value >= 10000000:
            # Translators: this is a short representation for a bounty >= 10 000 000 credits (m stands for million)
            readable = _(u"{} m").format(self.value / 1000000)
        elif self.value > 1000000:
            # Translators: this is a short representation for a bounty >= 1 000 000 credits (m stands for million)
            readable = _(u"{:.1f} m").format(self.value / 1000000.0)
        elif self.value >= 10000:
            # Translators: this is a short representation for a bounty >= 10 000 credits (k stands for kilo, i.e. thousand)
            readable = _(u"{} k").format(self.value / 1000)
        elif self.value >= 1000:
            # Translators: this is a short representation for a bounty >= 1000 credits (k stands for kilo, i.e. thousand)
            readable = _(u"{:.1f} k").format(self.value / 1000.0)
        else:
            # Translators: this is a short representation for a bounty < 1000 credits (i.e. shows the whole bounty, unabbreviated)
            readable = _(u"{}").format(self.value)
        return readable

class EDVehicles(object):
    CANONICAL_SHIP_NAMES = json.loads(open(os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'data/shipnames.json')).read())

    @staticmethod
    def canonicalize(name):
        if name is None:
            return u"Unknown"

        if name.lower() in EDVehicles.CANONICAL_SHIP_NAMES:
            return EDVehicles.CANONICAL_SHIP_NAMES[name.lower()]

        return name.lower()

class EDLocation(object):
    def __init__(self, star_system=None, place=None, security=None):
        self.star_system = star_system
        self.place = place
        self.security = security
    
    def is_anarchy_or_lawless(self):
        return self.security in ["$GAlAXY_MAP_INFO_state_anarchy;", "$GALAXY_MAP_INFO_state_lawless;"]

    def pretty_print(self):
        location = u"{system}".format(system=self.star_system)
        if self.place and self.place != self.star_system:
            if self.place.startswith(self.star_system + " "):
                # Translators: this is a continuation of the previous item (location of recently sighted outlaw) and shows a place in the system (e.g. supercruise, Cleve Hub) 
                location += u", {place}".format(place=self.place.partition(self.star_system + " ")[2])
            else:
                location += u", {place}".format(place=self.place)
        return location

class EDCmdr(object):
    def __init__(self):
        self.name = None
        self._ship = None
        self.location = EDLocation()
        self.game_mode = None
        self.previous_mode = None
        self.previous_wing = set()
        self.from_birth = False
        self._timestamp = edtime.EDTime()
        self.wing = set()
        self.friends = set()

    def in_solo_or_private(self):
        return self.game_mode in ["Solo", "Group"]

    def in_open(self):
        return self.game_mode == "Open"

    def inception(self):
        self.from_birth = True
        self.previous_mode = None
        self.previous_wing = set()
        self.wing = set()

    def killed(self):
        self.previous_mode = self.game_mode 
        self.previous_wing = self.wing.copy()
        self.game_mode = None
        self.wing = set()

    def resurrect(self):
        self.game_mode = self.previous_mode 
        self.wing = self.previous_wing.copy()
        self.previous_mode = None
        self.previous_wing = set()

    def leave_wing(self):
        self.wing = set()

    def join_wing(self, others):
        self.wing = set(others)

    def add_to_wing(self, other):
        self.wing.add(other)

    def is_friend_or_in_wing(self, interlocutor):
        return interlocutor in self.friends or interlocutor in self.wing

    @property
    def ship(self):
        return self._ship

    @ship.setter
    def ship(self, new_ship):
        self._ship = EDVehicles.canonicalize(new_ship)

    @property
    def timestamp(self):
        return self._timestamp.as_journal_timestamp()

    @timestamp.setter
    def timestamp(self, ed_timestamp):
        self._timestamp.from_journal_timestamp(ed_timestamp)

    def timestamp_js_epoch(self):
        return self._timestamp.as_js_epoch()

    @property
    def star_system(self):
        return self.location.star_system

    @star_system.setter
    def star_system(self, star_system):
        self.location.star_system = star_system

    @property
    def place(self):
        if self.location.place is None:
            # Translators: this is used when a location, comprised of a system and a place (e.g. Alpha Centauri & Hutton Orbital), has no place specified
            return _c(u"For an unknown or missing place|Unknown")
        return self.location.place

    @place.setter
    def place(self, place):
        self.location.place = place

    def location_security(self, ed_security_state):
        self.location.security = ed_security_state

    def in_bad_neighborhood(self):
        return self.location.is_anarchy_or_lawless()

    @star_system.setter
    def star_system(self, star_system):
        self.location.star_system = star_system


    def has_partial_status(self):
        return self._ship is None or self.location.star_system is None or self.location.place is None


    def update_ship_if_obsolete(self, ship, ed_timestamp):
        if self._ship is None or self._ship != EDVehicles.canonicalize(ship):
            EDRLOG.log(u"Updating ship info (was missing or obsolete). {old} vs. {ship}".format(old=self._ship, ship=ship), "DEBUG")
            self._ship = EDVehicles.canonicalize(ship)
            self._timestamp.from_journal_timestamp(ed_timestamp)
            return True

        return False


    def update_star_system_if_obsolete(self, star_system, ed_timestamp):
        if self.location.star_system is None or self.location.star_system != star_system:
            EDRLOG.log(u"Updating system info (was missing or obsolete). {old} vs. {system}".format(old=self.location.star_system, system=star_system), "INFO")
            self.location.star_system = star_system
            self._timestamp.from_journal_timestamp(ed_timestamp)
            return True

        return False


    def update_place_if_obsolete(self, place, ed_timestamp):
        if self.location.place is None or self.location.place != place:
            EDRLOG.log(u"Updating place info (was missing or obsolete). {old} vs. {place}".format(old=self.location.place, place=place), "INFO")
            self.location.place = place
            self._timestamp.from_journal_timestamp(ed_timestamp)
            return True

        return False
