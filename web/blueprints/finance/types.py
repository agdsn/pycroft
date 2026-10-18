import typing as t

from web.blueprints.finance.forms import ActivityMatchForm


class CombinedActivityMatchForm(t.Protocol):
    user: ActivityMatchForm
    team: ActivityMatchForm
