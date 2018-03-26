# coding: utf-8
from datetime import datetime
import re
import numpy as np
import pandas as pd

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import text, bindparam, func
from gmot.data.DbAccessor import DBAccessor, GBTweet
from eurekabot.DataModel import Tweet
import eurekabot.Constants as C


class EurekaDbAccessor(DBAccessor):
    # attention: max score matched with other rows, return some records have the same meta_ids_name-stage_mode keys.
    sql_best_score_by_user = text("""
        select 
            gb_tweets.meta_ids_name,
            gb_tweets.stage_mode,
            max_tweets.final_score,
            gb_tweets.is_score_edited
        from
            gb_tweets,
            (select
                gb_tweets.meta_ids_name,
                gb_tweets.stage_mode,
                MAX(gb_tweets.final_score) as final_score
            from
                gb_tweets
            where
                gb_tweets.user_id = :user_id and
                gb_tweets.is_valid_data = '0'
            group by
                gb_tweets.meta_ids_name,
                gb_tweets.stage_mode) max_tweets
        where
            gb_tweets.user_id = :user_id and
            gb_tweets.meta_ids_name = max_tweets.meta_ids_name and 
            gb_tweets.stage_mode = max_tweets.stage_mode and
            gb_tweets.final_score = max_tweets.final_score
    """, bindparams=[bindparam('user_id')])

    # rs = session.execute(sql_sample, {'user_id': tw.user_id}).fetchall()

    def __init__(self):
        super().__init__()

    def select_best_final_score(self, tw: Tweet):
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()

        final_score = 0
        gb_tweet = None
        rec_exists = True
        try:
            gb_tweet = (session
                        .query(func.max(GBTweet.final_score))
                        .filter(
                            GBTweet.user_id == tw.user_id,
                            GBTweet.meta_ids_name == tw.meta_ids_name,
                            GBTweet.stage_mode == tw.stage_mode,
                        )
                        .group_by(
                            GBTweet.user_id,
                            GBTweet.meta_ids_name,
                            GBTweet.stage_mode
                        )
                        .one())

            if len(gb_tweet) != 0:
                final_score = gb_tweet[0]
            else:
                rec_exists = False
        finally:
            session.commit()
            session.close()

        return final_score, rec_exists

    def select_final_score_with_tweet_id(self, tw: Tweet):
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()

        gb_tweet = None
        rec_exists = True
        try:
            try:
                gb_tweet = (session
                            .query(GBTweet.final_score)
                            .filter(
                                GBTweet.id == tw.tweet_id
                            )
                            .one())
            except NoResultFound as e:
                rec_exists = False
        finally:
            session.commit()
            session.close()

        return gb_tweet.final_score if rec_exists else 0, rec_exists

    def select_stage_scores(self, tw: Tweet):
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()

        rec_exists = True
        try:
            gb_tweets = session.execute(
                self.sql_best_score_by_user,
                {'user_id': tw.user_id}).fetchall()
        finally:
            session.commit()
            session.close()

        gb_tweets_dict_list = []
        if gb_tweets is not None and len(gb_tweets) != 0:
            for gb_tweet in gb_tweets:
                appended_sid_list = []
                if gb_tweet.meta_ids_name not in appended_sid_list:
                    sid = f"{gb_tweet.meta_ids_name}_{gb_tweet.stage_mode}"
                    gb_tweets_dict_list.append({key: value for key, value in gb_tweet.items()})
                    appended_sid_list.append(sid)

        else:
            rec_exists = False

        return gb_tweets_dict_list, rec_exists

    def modify_final_score_with_tweet_id(self, tw: Tweet, target_tw: Tweet):
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()

        gb_tweet = None
        rec_exists = True
        try:
            try:
                gb_tweet = (session
                            .query(GBTweet)
                            .with_for_update()
                            .filter(
                                GBTweet.id == target_tw.tweet_id
                            )
                            .one())
            except NoResultFound as e:
                rec_exists = False

            if rec_exists:
                gb_tweet.updated_at = datetime.now()
                gb_tweet.final_score = tw.final_score
                gb_tweet.is_score_edited = '1'
        finally:
            session.commit()
            session.close()

        return rec_exists

    def delete_result(self, tw: Tweet, target_tw: Tweet):
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()

        gb_tweet = None
        rec_exists = True
        try:
            try:
                gb_tweet = (session
                            .query(GBTweet)
                            .with_for_update()
                            .filter(
                                GBTweet.id == target_tw.tweet_id
                            )
                            .one())
            except NoResultFound as e:
                rec_exists = False

            if rec_exists:
                session.delete(gb_tweet)
                tw.record_mode = C.DB_RECORD_DELETE
        finally:
            session.commit()
            session.close()

        return rec_exists

    def insert_result(self, tw: Tweet):
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()
        now = datetime.now()

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

        try:
            session.add(gb_tweet)
            tw.record_mode = C.DB_RECORD_INSERT
        finally:
            session.commit()
            session.close()

        return tw

    # no use
    def upsert_result(self, tw: Tweet):
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()
        now = datetime.now()

        gb_tweet = None
        try:
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

            update_flg = None
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
                tw.record_mode = C.DB_RECORD_INSERT
            elif tw.final_score >= tw.prev_final_score:
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
                tw.record_mode = C.DB_RECORD_UPDATE
            elif tw.final_score < tw.prev_final_score:
                tw.record_mode = C.DB_RECORD_NOT_UPDATE
        finally:
            session.commit()
            session.close()

        return tw

    @staticmethod
    def sanitize_itr_obj(list_str):
        conv_str = re.sub(r'[\{\}\[\]\']', '', str(list_str))
        conv_str = re.sub(r' +', ' ', conv_str)
        return conv_str
