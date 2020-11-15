from dataclasses import dataclass, asdict
from typing import List, Optional
from copy import deepcopy

import attr

from infinitdserver.battleground_state import BattlegroundState
from infinitdserver.game_config import ConfigId

@attr.s(auto_attribs=True, eq=True)
class UserSummary:
    uid: str
    name: str
    gold: float
    accumulatedGold: float
    goldPerMinute: float
    inBattle: bool
    wave: List[ConfigId]

@attr.s(auto_attribs=True, frozen=True)
class FrozenUserSummary(UserSummary):
    pass

@attr.s(auto_attribs=True, eq=True)
class User(UserSummary):
    battleground: BattlegroundState

@attr.s(auto_attribs=True, frozen=True)
class FrozenUser(User):
    pass

class MutableUser:
    _original_user: User
    _user: User

    # Should only be made from MutableUserContext.
    def __init__(self, user: User):
        super(MutableUser, self).__setattr__('_original_user', deepcopy(user))
        super(MutableUser, self).__setattr__('_user', deepcopy(user))

    @property
    def battlegroundModified(self):
        return self._original_user.battleground != self._user.battleground

    @property
    def summaryModified(self):
        # It feels like there should be a better way to do this with super
        return not super(User, self._original_user).__eq__(self._user)

    @property
    def waveModified(self):
        return self._original_user.wave != self._user.wave

    def resetBattleground(self):
        self.battleground = self.originalBattleground
        self._originalBattleground = None

    def addGold(self, gold):
        self.gold += gold
        self.accumulatedGold += gold

    def __getattr__(self, name):
        if name == "user": # Make user property read-only
            return self._user
        return getattr(self._user, name)

    def __setattr__(self, name, value):
        try:
            setattr(self._user, name, value)
        except AttributeError as e:
            raise e
