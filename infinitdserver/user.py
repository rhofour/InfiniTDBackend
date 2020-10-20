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
    gold: int
    accumulatedGold: int
    goldPerMinute: int
    inBattle: bool
    wave: List[ConfigId]

@attr.s(auto_attribs=True, frozen=True)
class FrozenUserSummary(UserSummary):
    pass

@attr.s(auto_attribs=True, eq=True)
class User(UserSummary):
    battleground: BattlegroundState

    def compareAsUserSummary(self, other: UserSummary):
        print(f"original: {self}")
        print(f"other   : {other}")
        return (self.uid == other.uid and self.name == other.name and
                self.gold == other.gold and
                self.accumulatedGold == other.accumulatedGold and
                self.goldPerMinute == other.goldPerMinute and
                self.inBattle == other.inBattle and self.wave == other.wave)

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
        #return not self._original_user.compareAsUserSummary(self._user)
        return not super(User, self._original_user).__eq__(self._user)

    @property
    def waveModified(self):
        return self._original_user.wave != self._user.wave

    def resetBattleground(self):
        self.battleground = self.originalBattleground
        self._originalBattleground = None

    def __getattr__(self, name):
        if name == "user": # Make user property read-only
            return self._user
        return getattr(self._user, name)

    def __setattr__(self, name, value):
        try:
            setattr(self._user, name, value)
            #super(MutableUser, self).__setattr__(name, value)
        except AttributeError as e:
            raise e
