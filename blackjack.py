from nameko_sqlalchemy import Session
from nameko.rpc import rpc

from sqlalchemy import and_
from sqlalchemy.sql.expression import func

from models import Match, Player, Deck, Card, Hand, Base


class BlackJackService:
    name = "blackjack"
    session = Session(Base)

    @rpc
    def hit(self, match_uuid, player_id):
        '''
        Hit and pop a card `out` of the table adding it to the hand, only if game has not ended
        '''
        if self._get_winner(match_uuid, player_id) == 0:
            card_id = self._pop_card(match_uuid)
            self.session.add(Hand(card_id=card_id, match_uuid=match_uuid, player_id=player_id))
            self.session.commit()

        return self.show(match_uuid, player_id)

    @rpc
    def stick(self, match_uuid, player_id):
        '''
        Stick method that starts the dealer play, only if game has not ended
        '''
        if self._get_winner(match_uuid, player_id) == 0:
            dealer_id = self._get_dealer(match_uuid, player_id)
            self._dealer_play(match_uuid, dealer_id, player_id)

        return self.show(match_uuid, player_id)

    @rpc
    def show(self, match_uuid, player_id):
        '''
        Return the status of the current game, player winner var wins over hands evaluation
        '''
        dealer_id = self._get_dealer(match_uuid, player_id)

        player_score = self._score(match_uuid, player_id)
        dealer_score = self._score(match_uuid, dealer_id)

        # check database first to see if there is a winner
        result = self._get_winner(match_uuid, player_id) or self._evaluator(player_score, dealer_score)
        status = ''

        if result == 1:
            self._set_result(match_uuid, player_id)
            status = 'Player won'
        elif result == -1:
            self._set_result(match_uuid, player_id, winner=False)
            status = 'Dealer won'
        else:
            status = 'Game still being played'

        return {
            'match_uuid': match_uuid,
            'player_id': player_id,
            'dealer_id': dealer_id,
            'game': status,
            'score': {
                'player': 'L: {}, H: {}, played hands: {}'.format(*player_score),
                'dealer': 'L: {}, H: {}, played hands: {}'.format(*dealer_score),
            }
        }

    @rpc
    def new_match(self):
        '''
        Exposed method to kickoff a match, creating the Match object and then offloading to the init method
        '''
        match = Match()
        self.session.add(match)
        self.session.commit()
        return self.init_match(match.uuid)

    def init_match(self, match_uuid):
        '''
        Start up a match with the deck creation and the first 3 moves/hands
        '''
        match = self.session.query(Match).get(match_uuid)
        if match is None:
            return {'error': 'No match found'}

        self._make_deck(match_uuid)
        dealer_id, player_id = self._make_players(match_uuid)

        # first dealing of cards
        for i in range(2):
            self.hit(match_uuid, player_id)
        self.hit(match_uuid, dealer_id)

        return self.show(match_uuid, player_id)

    def _make_players(self, match_uuid):
        '''
        Create a player and a dealer
        '''
        dealer = Player(match_uuid=match_uuid)
        player = Player(match_uuid=match_uuid)

        self.session.add(dealer)
        self.session.add(player)
        self.session.commit()

        return [dealer.id, player.id]

    def _make_deck(self, match_uuid):
        '''
        Deck builder
        '''
        deck = Deck(match_uuid=match_uuid)
        for seed in ['Hearts', 'Clubs', 'Spades', 'Diamonds']:
            for number in range(1, 14):
                card = self._make_card(seed, number)
                deck.cards.append(card)

        self.session.add(deck)
        self.session.commit()

    def _make_card(self, seed, number):
        '''
        Card builder
        '''
        card = Card(seed=seed, number=number)

        if number == 1:
            card.low_value = 1
            card.high_value = 11
        elif number > 10:
            card.low_value = 10
            card.high_value = 10
        else:
            card.low_value = number
            card.high_value = number

        return card

    def _pop_card(self, match_uuid):
        '''
        Pop a card from the table, chosing randomly from the unpicked cards makes up for the shuffling, therefore no
        need to store the order of the cards
        SQL =>
        select * from card join deck on card.deck_id = deck.id
        where card.id not in (
            select card_id from hand where hand.match_uuid = '67aa6e5f-69dc-471e-9e58-c0d7210a9ead'
        ) and deck.match_uuid = '67aa6e5f-69dc-471e-9e58-c0d7210a9ead' order by random() limit 1;
        '''
        subquery = self.session.query(Hand.card_id).filter(Hand.match_uuid == match_uuid)
        card = self.session.query(Card).join(Deck).filter(
            and_(Deck.match_uuid == match_uuid, ~Card.id.in_(subquery))
        ).order_by(func.random()).first()
        return card.id

    def _set_result(self, match_uuid, player_id, winner=True):
        '''
        Set the winner of the game
        '''
        dealer_id = self._get_dealer(match_uuid, player_id)
        winner_id = player_id if winner else dealer_id

        self.session.query(Player).filter(Player.id == winner_id).update({'winner': True})
        self.session.commit()

    def _get_winner(self, match_uuid, player_id):
        '''
        Get the winner
        '''
        dealer_id = self._get_dealer(match_uuid, player_id)

        if self.session.query(Player).get(player_id).winner is True:
            return 1
        elif self.session.query(Player).get(dealer_id).winner is True:
            return -1
        else:
            return 0

    def _get_dealer(self, match_uuid, player_id):
        '''
        Get the dealer id, by selecting the "other player" of the match, given there can only be 2
        '''
        match = self.session.query(Match).get(match_uuid)
        dealer_id = [player.id for player in match.players if player.id != player_id][0]
        return dealer_id

    def _score(self, match_uuid, player_id):
        '''
        Returns a list with the low score, high score and # of played hands
        SQL =>
            Select sum(card.lvalue), sum(card.hvalue)
            from hand join card on card.id = hand.card_id
            where hand.player_id = player and match_uuid = match
        '''
        scores = self.session.query(
            func.sum(Card.low_value), func.sum(Card.high_value), func.count(Hand.id)
        ).join(Hand).filter(
            and_(Hand.match_uuid == match_uuid, Hand.player_id == player_id)
        )
        low, high, hands = scores.all()[0]

        return [low or 0, high or 0, hands or 0]

    def _evaluator(self, player_score, dealer_score):
        '''
        Return 1 if player won, -1 for a dealer win, 0 for any other result like 'still playing'
        Player wins if it scores 21 in 2 hands or has the score of 21, to make it easier I assumed that it prevails
        on dealer 21, no time left to code around that
        Dealer wins if it scores 21, if the player went bust (with lowest value of cards)

        If dealer has not 17 in its hand, game is not done yet
        '''

        # player best score is high-score if high_score < 22 else low_score

        player_best_score = player_score[1] if max(player_score[1], 22) == 22 else player_score[0]
        dealer_best_score = dealer_score[1] if max(dealer_score[1], 22) == 22 else dealer_score[0]

        if player_best_score < 21 and dealer_score[2] < 2:
            # dealer hasn't played yet and player didn't go bust
            return 0
        elif any(
            [
                player_best_score == 21,
                dealer_best_score > 21,
                (dealer_score[2] > 1 and dealer_best_score <= player_best_score <= 21)
            ]
        ):
            return 1
        elif any(
            [
                player_best_score > 21,
                (dealer_score[2] > 1 and 17 < dealer_best_score <= 21 and player_best_score < dealer_best_score)
            ]
        ):
            return -1
        else:
            return 0

    def _dealer_play(self, match_uuid, dealer_id, player_id):
        '''
        Dealer plays until it reaches at least 18 (rule from wikipedia)
        '''

        low, high, hands = self._score(match_uuid, dealer_id)
        while min(low, high) <= 17:
            card_id = self._pop_card(match_uuid)
            self.session.add(Hand(card_id=card_id, match_uuid=match_uuid, player_id=dealer_id))
            self.session.commit()

            low, high, hands = self._score(match_uuid, dealer_id)
