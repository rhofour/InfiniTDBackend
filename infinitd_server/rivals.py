from typing import List, Optional

import attr

@attr.s(auto_attribs=True, eq=True)
class Rivals:
    aheadNames: List[str]
    behindNames: List[str]