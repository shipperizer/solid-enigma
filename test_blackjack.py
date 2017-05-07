from unittest import mock
from uuid import uuid4

import pytest
from nameko.testing.services import worker_factory

from blackjack import BlackJackService
from models import Hand


@pytest.fixture()
def service():
    return worker_factory(BlackJackService)


@pytest.mark.parametrize(
    'player_score, dealer_score, expect',
    [
        ([18, 18, 3], [19, 19, 2], -1), ([22, 22, 3], [19, 19, 2], -1), ([20, 20, 3], [19, 19, 2], 1),
        ([12, 32, 3], [18, 18, 2], -1), ([20, 20, 3], [20, 20, 2], 1), ([12, 32, 3], [21, 21, 2], -1),
        ([12, 32, 3], [20, 29, 3], -1), ([12, 32, 3], [29, 29, 3], 1),
    ]
)
def test_evaluator(player_score, dealer_score, expect, service):
    assert service._evaluator(player_score, dealer_score) == expect


def test_new_match_calls_init(service):
    with mock.patch.object(service, 'init_match') as init_match:
        service.new_match()
        assert service.session.add.called
        assert service.session.commit.called
        assert init_match.called


def test_hit(service):
    match = str(uuid4())
    with mock.patch.object(service, '_get_winner', return_value=0) as get_winner, mock.patch.object(service, '_pop_card', return_value=1) as pop_card, mock.patch.object(service, 'show') as show:
        service.hit(match, 1)
        assert service.session.add.called_with(Hand(card_id=1, match_uuid=match, player_id=1))
        assert service.session.commit.called
        assert show.called_with(match, 1)


def test_stick(service):
    match = str(uuid4())
    with mock.patch.object(service, '_get_dealer', return_value=0) as get_dealer, mock.patch.object(service, '_dealer_play') as dealer_play, mock.patch.object(service, 'show') as show:
        service.stick(match, 1)
        assert get_dealer.called_with(match, 1)
        assert dealer_play.called_with(match, 0, 1)
        assert show.called_with(match, 1)


def test_show(service):
    match = str(uuid4())
    with mock.patch.object(service, '_get_dealer', return_value=0) as get_dealer, \
        mock.patch.object(service, '_score', side_effect=[[15, 15, 2], [21, 21, 2]]) as score, \
        mock.patch.object(service, '_get_winner', return_value=0) as get_winner, \
        mock.patch.object(service, '_set_result') as set_result:

        result = service.show(match, 1)
        assert get_dealer.called_with(match, 1)
        assert score.called
        assert set_result.called

        assert result['match_uuid'] == match
        assert result['dealer_id'] == 0
        assert result['player_id'] == 1
        assert result['game'] == 'Dealer won'
