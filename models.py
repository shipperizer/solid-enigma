from uuid import uuid4

from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()


class Match(Base):
    __tablename__ = 'match'
    uuid = Column(UUID, default=lambda: str(uuid4()), primary_key=True)


class Player(Base):
    __tablename__ = 'player'
    id = Column(Integer, primary_key=True)
    match_uuid = Column(UUID, ForeignKey('match.uuid'))
    winner = Column(Boolean, default=False)

    match = relationship('Match', backref='players')


class Deck(Base):
    __tablename__ = 'deck'
    id = Column(Integer, primary_key=True)
    match_uuid = Column(UUID, ForeignKey('match.uuid'))

    match = relationship('Match', backref='decks')


class Card(Base):
    __tablename__ = 'card'
    id = Column(Integer, primary_key=True)
    deck_id = Column(Integer, ForeignKey('deck.id'))
    seed = Column(String)
    number = Column(Integer)
    low_value = Column(Integer)
    high_value = Column(Integer)

    deck = relationship('Deck', backref='cards')


class Hand(Base):
    __tablename__ = 'hand'
    id = Column(Integer, primary_key=True)
    match_uuid = Column(UUID, ForeignKey('match.uuid'))
    player_id = Column(Integer, ForeignKey('player.id'))
    card_id = Column(Integer, ForeignKey('card.id'))

    match = relationship('Match', backref='hands')
    card = relationship('Card', uselist=False, backref='hand')
    player = relationship('Player', backref='hands')
