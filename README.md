# solid-enigma

# Blackjack RPC Server

Nameko application that exposes RPC calls to play blackjack in a 1vsDealer game

Python app is split between the `blackjack.py` and `models.py` (where all the db stuff resides)
I used alembic to create the db and handle the migration (maybe overkill, but I'm kinda used to it and it works great)
In the Makefile there are a series of useful commands/targets that are used by the deployment, you can find a dockerfile and a docker-compose to handle the infrastructure/dev environment

To run simply do `docker-compose up`, a rabbitmq server, a postgres and the nameko app will start, the nameko app triggers the migration with alembic on startup
Check the Makefile targets for more info


Example of gameplay:

```
match = n.rpc.blackjack.new_match()
print(match)
{'match_uuid': 'd403869c-a507-41ec-a2c1-8151835c9b14', 'player_id': 6, 'dealer_id': 5, 'game': 'Game still being played', 'score': {'player': 'L: 14, H: 14, played hands: 2', 'dealer': 'L: 1, H: 11, played hands: 1'}}
player = match['player_id']
match_uuid = match['match_uuid']
hand_0 = n.rpc.blackjack.hit(match_uuid, player)
print(hand_0)
{'match_uuid': 'd403869c-a507-41ec-a2c1-8151835c9b14', 'player_id': 6, 'dealer_id': 5, 'game': 'Dealer won', 'score': {'player': 'L: 24, H: 24, played hands: 3', 'dealer': 'L: 1, H: 11, played hands: 1'}}
hand_1 = n.rpc.blackjack.stick(match_uuid, player)
print(hand_1)
{'match_uuid': 'd403869c-a507-41ec-a2c1-8151835c9b14', 'player_id': 6, 'dealer_id': 5, 'game': 'Dealer won', 'score': {'player': 'L: 24, H: 24, played hands: 3', 'dealer': 'L: 20, H: 30, played hands: 4'}}
print(n.rpc.blackjack.show(match_uuid, player))
{'match_uuid': 'd403869c-a507-41ec-a2c1-8151835c9b14', 'player_id': 6, 'dealer_id': 5, 'game': 'Dealer won', 'score': {'player': 'L: 24, H: 24, played hands: 3', 'dealer': 'L: 20, H: 30, played hands: 4'}}
```

# Improvements and thoughts

* tests are not super meaningful, I just managed to test the wiring between the methods, I gave it a go at implementing proper integration tests without good success so after a while spent on them i gave up...definitely a point ot improve [here](https://nameko.readthedocs.io/en/stable/testing.html#integration-testing)
* the design is a bit too complex, would totally refactor by moving the `store layer` methods in a separate microservice provided that the number of methods increased, at the same time starting with 2 separate microservices would have been too much of a pre-optimization
* the db schema could be improved by using a shared deck, at the same time though in the beginning i started to consider that if i had multiple players in a game, that might have been tricky due to the presence of multiple decks, therefore I opted for this decision. I must admit that you cannot really see any benefit in it at the moment but if the number of features required increases that could be a good solution
* the card order in the deck and the shuffling have been substituted by the `order by random()`, looked like a cleaned solution to avoid another useless field on the deck or card table to mantain the order (even though it's arguably harder to understand)
* the evaluator method holds all the winning logic, I might be missing something but should be trivial to add clauses to it to extend
