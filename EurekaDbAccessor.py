# coding: utf-8
from datetime import datetime
import re
import numpy as np
import pandas as pd

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from gmot.data.DbAccessor import DBAccessor, GBTweet
from eurekabot.DataModel import Tweet


class EurekaDbAccessor(DBAccessor):

    def __init__(self):
        super().__init__()

    def select_prev_final_score(self, tw: Tweet):
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()

        gb_tweet = None
        rec_exists = True
        try:
            gb_tweet = (session
                        .query(GBTweet.final_score)
                        .with_for_update()
                        .filter(
                            GBTweet.user_id == tw.user_id,
                            GBTweet.meta_ids_name == tw.meta_ids_name,
                            GBTweet.stage_mode == tw.stage_mode,
                        )
                        .one())
        except NoResultFound as e:
            rec_exists = False

        session.commit()
        session.close()

        return gb_tweet.final_score if rec_exists else 0, rec_exists

    def select_specified_status_final_score(self, tw: Tweet):
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()

        gb_tweet = None
        rec_exists = True
        try:
            gb_tweet = (session
                        .query(GBTweet.final_score)
                        .with_for_update()
                        .filter(
                            GBTweet.tweet_id == tw.tweet_id
                        )
                        .one())
        except NoResultFound as e:
            rec_exists = False

        session.commit()
        session.close()

        return gb_tweet.final_score if rec_exists else 0, rec_exists

    def select_stage_scores(self, tw: Tweet):
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()

        rec_exists = True
        gb_tweets = (session
                     .query(GBTweet.meta_ids_name,
                            GBTweet.stage_mode,
                            GBTweet.final_score,
                            GBTweet.is_score_edited
                            )
                     .with_for_update()
                     .filter(
                        GBTweet.user_id == tw.user_id
                     )
                     .all())

        session.commit()
        session.close()

        gb_tweets_dict_list = []
        if gb_tweets is not None and len(gb_tweets) != 0:
            for gb_tweet in gb_tweets:
                gb_tweet_dict = gb_tweet._asdict()
                gb_tweets_dict_list.append(gb_tweet_dict)
        else:
            rec_exists = False

        return gb_tweets_dict_list, rec_exists

    def modify_final_score(self, tw: Tweet, target_tw: Tweet):
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()

        gb_tweet = None
        rec_exists = True
        try:
            gb_tweet = (session
                        .query(GBTweet)
                        .with_for_update()
                        .filter(
                            GBTweet.tweet_id == target_tw.tweet_id,
                            # GBTweet.meta_ids_name == target_tw.meta_ids_name,
                            # GBTweet.stage_mode == target_tw.stage_mode
                        )
                        .one())
        except NoResultFound as e:
            rec_exists = False

        if rec_exists:
            gb_tweet.updated_at = datetime.now()
            gb_tweet.final_score = tw.final_score
            gb_tweet.is_score_edited = '1'

        session.commit()
        session.close()

        return rec_exists

    def delete_result(self, tw: Tweet, target_tw: Tweet):
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()

        gb_tweet = None
        rec_exists = True
        try:
            gb_tweet = (session
                        .query(GBTweet)
                        .with_for_update()
                        .filter(
                            GBTweet.tweet_id == target_tw.tweet_id,
                            # GBTweet.meta_ids_name == target_tw.meta_ids_name,
                            # GBTweet.stage_mode == target_tw.stage_mode
                        )
                        .one())
        except NoResultFound as e:
            rec_exists = False

        if rec_exists:
            session.delete(gb_tweet)

        session.commit()
        session.close()

        return rec_exists

    def upsert_result(self, tw: Tweet):
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()
        now = datetime.now()

        gb_tweet = None
        if tw.rec_exists is not None and tw.rec_exists is True:
            try:
                gb_tweet = (session
                            .query(GBTweet)
                            .with_for_update()
                            .filter(
                                GBTweet.user_id == tw.user_id,
                                GBTweet.meta_ids_name == tw.meta_ids_name,
                                GBTweet.stage_mode == tw.stage_mode,
                            )
                            .one())
            except NoResultFound as e:
                # irregular
                tw.rec_exists = False

        if not tw.rec_exists:
            gb_tweet = GBTweet(
                now,
                '0000-00-00 00:00:00',
                tw.user_id,
                tw.meta_ids_name,
                tw.stage_mode,
                tw.screen_name,
                tw.tweet_id,
                tw.post_date,
                self.sanitize_itr_obj(tw.hash_tags),
                tw.final_score,
                tw.total_score,
                self.sanitize_itr_obj(np.array(tw.total_score_probas).round(2)),
                tw.post_datetime,
                tw.text,
                tw.is_score_edited,
                tw.is_valid_data
            )
            session.add(gb_tweet)
        elif tw.final_score > tw.prev_final_score:
            gb_tweet.updated_at = now
            gb_tweet.tweet_id = tw.tweet_id
            gb_tweet.post_date = tw.post_date
            gb_tweet.hash_tags = self.sanitize_itr_obj(tw.hash_tags)
            gb_tweet.final_score = tw.final_score
            gb_tweet.total_score = tw.total_score
            gb_tweet.total_score_probas = self.sanitize_itr_obj(np.array(tw.total_score_probas).round(2))
            gb_tweet.post_datetime = tw.post_datetime
            gb_tweet.text = tw.text
            gb_tweet.is_score_edited = tw.is_score_edited
            gb_tweet.is_valid_data = tw.is_valid_data

        session.commit()
        session.close()

        return True

    @staticmethod
    def sanitize_itr_obj(list_str):
        conv_str = re.sub(r'[\{\}\[\]\']', '', str(list_str))
        conv_str = re.sub(r' +', ' ', conv_str)
        return conv_str
