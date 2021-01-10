from dataclasses import dataclass, asdict
from typing import List, Optional
from copy import deepcopy
import sqlite3

import attr

from infinitd_server.battleground_state import BattlegroundState, BgTowersState
from infinitd_server.game_config import ConfigId

@attr.s(auto_attribs=True, eq=True)
class UserSummary:
    uid: str
    name: str
    gold: float
    accumulatedGold: float
    goldPerMinute: float
    wave: List[ConfigId]
    inBattle: bool = False
    admin: bool = False

@attr.s(auto_attribs=True, frozen=True)
class FrozenUserSummary(UserSummary):
    pass

@attr.s(auto_attribs=True, eq=True)
class User(UserSummary):
    battleground: BattlegroundState = BattlegroundState(towers=BgTowersState(towers=[]))

@attr.s(auto_attribs=True, frozen=True)
class FrozenUser(User):
    pass

class MutableUser:
    _originalUser: User
    _user: User
    conn: Optional[sqlite3.Connection]

    # Should only be made from MutableUserContext.
    def __init__(self, user: User, conn: Optional[sqlite3.Connection]):
        super(MutableUser, self).__setattr__('_originalUser', deepcopy(user))
        super(MutableUser, self).__setattr__('_user', deepcopy(user))
        super(MutableUser, self).__setattr__('conn', conn)

    @property
    def battlegroundModified(self):
        return self._originalUser.battleground != self._user.battleground

    @property
    def summaryModified(self):
        # It feels like there should be a better way to do this with super
        return not super(User, self._originalUser).__eq__(self._user)

    @property
    def waveModified(self):
        return self._originalUser.wave != self._user.wave

    def reset(self):
        super(MutableUser, self).__setattr__('_user', deepcopy(self._originalUser))

    def addGold(self, gold):
        self.gold += gold
        self.accumulatedGold += gold

    def __getattr__(self, name):
        if name == "user": # Make user property read-only
            return self._user
        if name == "conn":
            return self.conn
        return getattr(self._user, name)

    def __setattr__(self, name, value):
        try:
            setattr(self._user, name, value)
        except AttributeError as e:
            raise e
