from dataclasses import dataclass
from typing import Literal

BugType = Literal["LINTING", "SYNTAX", "LOGIC", "TYPE_ERROR", "IMPORT", "INDENTATION"]


@dataclass
class Failure:
    file: str
    line_number: int
    bug_type: BugType
    message: str


@dataclass
class FixPlan:
    file: str
    line_number: int
    bug_type: BugType
    commit_message: str
    expected_output: str
