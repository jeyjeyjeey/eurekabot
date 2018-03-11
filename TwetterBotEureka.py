# coding: utf-8
import sys
import os
import re
import unicodedata
import time
import logging
import configparser
import json
import pickle
import random
from datetime import datetime

from requests import get
from requests.exceptions import Timeout, RequestException
from ssl import SSLError

import tweepy
import cv2
import numpy as np

from gmot.gb.MvAnalyzer import clip_caputure, ajust_capture, ocr_total_score_cnn
from mlsp.ml.CNNClassifierDigit import CNNClassifierDigit
from mlsp.ml.CNNClassifierStaticObject import CNNClassifierStaticObject
import eurekabot.Constants as C
from eurekabot.ScoreEstimator import ScoreEstimator
from eurekabot.DataModel import Tweet
from eurekabot.EurekaDbAccessor import EurekaDbAccessor


def main():
    args = sys.argv
    config_file = './config.ini'
    if len(args) == 1:
        pass
    elif len(args) == 2:
        config_file = args[1]
    else:
        print('arguments error/Usage:[config_file] [log_dir]')
        exit(1)

    if not os.path.exists(config_file):
        print('FileNotFoundError/config_file not found')
        exit(1)

    config = configparser.ConfigParser()
    config.read(config_file)

    logging.basicConfig(
        filename=os.path.join(
            config.get("logging", "log_dir"),
            '{0}_{1}.log'.format(os.path.basename(__file__), datetime.now().strftime("%Y%m%d_%H%M%S"))),
        level=config.getint("logging", "log_level"), format='%(asctime)s %(message)s')

    api = authenticate(config)
    stream = create_stream(api, config)
    run_stream(api, stream, config)


class MyStreamListener(tweepy.StreamListener):
    digit_estimator = None
    score_estimator = None
    melonpan_classifier = None

    def __init__(self, api, ckpt_dir, weight_dir, db_config_file, serif_file):
        super().__init__(api)
        self.__me = self.api.me()
        self.__dbcf = db_config_file

        if MyStreamListener.digit_estimator is None:
            ts_clsfr = CNNClassifierDigit()
            ts_clsfr.ckpt_dir = ckpt_dir
            ts_clsfr.prepare_classify()
            MyStreamListener.digit_estimator = ts_clsfr

        if MyStreamListener.score_estimator is None:
            se = ScoreEstimator().prepare()
            MyStreamListener.score_estimator = se

        if MyStreamListener.melonpan_classifier is None:
            mp_clsfr = CNNClassifierStaticObject()
            mp_clsfr.weight_dir = weight_dir
            mp_clsfr.identifier = 'melonpan'
            mp_clsfr.classes = ['melonpan', 'guild_battle', 'others']
            mp_clsfr.dense_shape = [192, 96]
            mp_clsfr.prepare_classify()
            MyStreamListener.melonpan_classifier = mp_clsfr

        with open(serif_file, 'r') as f:
            self.__serif_dict = json.load(f)

    @property
    def me(self):
        return self.__me

    @property
    def dbcf(self):
        return self.__dbcf

    @property
    def serif_dict(self):
        return self.__serif_dict

    """
    event
        these func is automatically called when twitter api push
    """
    def on_status(self, status):
        tw = None
        if status.author.id == self.me.id:
            logging.debug('My tweet')
            return

        if hasattr(status, 'retweeted_status'):
            logging.debug('Retweet')
            return

        if self._check_reply_to_my_tweet(status):
            logging.info('Reply to my tweet')
            parent_tweet_status = self.api.get_status(status.in_reply_to_status_id)
            grand_parent_tweet_status = self.api.get_status(parent_tweet_status.in_reply_to_status_id)
            tw = self._pre_process(status)
            target_tw = self._pre_process(grand_parent_tweet_status)
            tw = self._process_reply_to_my_tweet(tw, target_tw)
        elif self._check_reply_or_mention_to_me(status):
            logging.info('Reply or mention to me')
            tw = self._pre_process(status)
            tw = self._process_reply_to_me(tw)
        elif self._contains_hashtags_stage(status):
            logging.info('Air reply to me')  # even if not a reply, she responds to tweets with hashtags and photos.
            tw = self._pre_process(status)
            tw = self._process_air_reply_to_me(tw)

        if tw is not None and logging.DEBUG == logging.getLogger().getEffectiveLevel():
            with open(f"./test_data/obj_status_{tw.process_mode}.pickle", 'wb') as pf:
                pickle.dump(status, pf)

        return

    def on_event(self, event):
        logging.info('event({}) occur'.format(event.event))
        if event.event == 'follow' and event.source['id'] != self.me.id:
            self.api.create_friendship(id=event.source['id'])
            logging.info('follow back：@{}(uid:{})'.format(event.source['screen_name'], event.source['id']))

    def on_error(self, status_code):
        if status_code == 420:
            return False

    """
    sub event
        these func is called from each events
    """
    def _process_reply_to_me(self, tw):
        text = str()
        tw.process_mode = C.MODE_OTHER
        if len(tw.photo_urls) != 0:
            tw.photos = self._http_request_photos(tw.photo_urls)
            if tw.photos is None:  # she does not respond, when attached files are not type/image.
                return tw
            tw.photo_classes, probas = self._classify_images(tw.photos)
            logging.debug('{}: {}'.format(tw.photo_classes, probas))

            tw.process_mode = self._decision_process_mode_with_photos(tw)
            if tw.process_mode in (C.MODE_GUILD, C.MODE_HMHM):
                tw = self._analyse_guild_battle(tw)
            elif tw.process_mode in (C.MODE_MP, C.MODE_GUILD_ERR_INVALID_HASHTAG, C.MODE_OTHER):
                pass
        elif C.HASHTAG_BEST_SCORE in tw.hash_tags:
            tw.process_mode = C.MODE_BEST_SCORE
            db = EurekaDbAccessor()
            db.prepare_connect(cf=self.dbcf)
            tw.best_scores_list, tw.rec_exists = db.select_stage_scores(tw)
            if not tw.rec_exists or len(tw.best_scores_list) == 0:
                tw.process_mode = C.MODE_THROUGH
        elif C.HASHTAG_STD_SCORE in tw.hash_tags:
            tw.process_mode = C.MODE_STD_SCORE
            db = EurekaDbAccessor()
            db.prepare_connect(cf=self.dbcf)
            tw.best_scores_list, tw.rec_exists = db.select_stage_scores(tw)
            if tw.rec_exists and len(tw.best_scores_list) != 0:
                tw.std_scores_dict = self._calculate_standard_scores(tw.best_scores_list)
            else:
                tw.process_mode = C.MODE_THROUGH

        if tw.process_mode != C.MODE_THROUGH:
            text = self._assemble_text(tw)
            self.api.update_status(status=text, in_reply_to_status_id=tw.tweet_id)

        return tw

    def _process_reply_to_my_tweet(self, tw, target_tw):
        text = str()
        tw.process_mode = C.MODE_THROUGH
        if target_tw.user_id == tw.user_id:
            tw.process_mode = self._decision_process_mode_in_reply_my_tweet(tw)
            if tw.process_mode == C.MODE_MOD:
                db = EurekaDbAccessor()
                db.prepare_connect(cf=self.dbcf)

                tw.final_score = self._convert_str_zen_to_han(re.findall(r"\d+", tw.text, re.U)[0])
                target_tw.rec_exists = db.modify_final_score(tw, target_tw)

                if target_tw.rec_exists:
                    sid = f"{target_tw.meta_ids_name}_{target_tw.stage_mode}"
                    tw.sfq, tw.escr_dict = MyStreamListener._estimate_scores(sid, tw.final_score)
                    if tw.sfq < 0.000001:
                        tw.process_mode = C.MODE_GUILD_ERR_ESTIMATE_SCORE
                    if tw.next_stage is None:
                        tw.next_stage = self._estimate_next_stage(target_tw)
                else:
                    tw.process_mode = C.MODE_MOD_RECORD_NOT_FOUND
            elif tw.process_mode == C.MODE_DELETE:
                db = EurekaDbAccessor()
                db.prepare_connect(cf=self.dbcf)
                target_tw.rec_exists = db.delete_result(tw, target_tw)
                if not target_tw.rec_exists:
                    tw.process_mode = C.MODE_MOD_RECORD_NOT_FOUND
            elif tw.process_mode == C.MODE_ANOTHER_STAGE_ESTIMATE:
                db = EurekaDbAccessor()
                db.prepare_connect(cf=self.dbcf)

                target_tw.final_score, target_tw.rec_exists = db.select_specified_status_final_score(target_tw)

                if target_tw.rec_exists:
                    sid = f"{target_tw.meta_ids_name}_{target_tw.stage_mode}"
                    tw.sfq, tw.escr_dict = MyStreamListener._estimate_scores(sid, target_tw.final_score)
                    if tw.sfq < 0.000001:
                        tw.process_mode = C.MODE_GUILD_ERR_ESTIMATE_SCORE
                    tw.next_stage = tw.meta_ids_name
                else:
                    tw.process_mode = C.MODE_MOD_RECORD_NOT_FOUND
            elif tw.process_mode in (C.MODE_MOD_UNIDENTIFY_SCORE):
                pass

        if tw.process_mode != C.MODE_THROUGH:
            text = self._assemble_text(tw)
            self.api.update_status(status=text, in_reply_to_status_id=tw.tweet_id)

        return tw

    def _process_air_reply_to_me(self, tw):
        text = str()
        tw.process_mode = C.MODE_THROUGH
        if len(tw.photo_urls) != 0 and len(tw.hash_tags) != 0:
            tw.photos = self._http_request_photos(tw.photo_urls)
            if tw.photos is None:  # she does not respond, when attached files are not type/image.
                return tw
            tw.photo_classes, probas = self._classify_images(tw.photos)

            tw.process_mode = self._decision_process_mode_with_photos(tw)
            if tw.process_mode in (C.MODE_GUILD, C.MODE_HMHM):
                tw = self._analyse_guild_battle(tw)
            else:
                tw.process_mode = C.MODE_THROUGH
                # no process: self.MODE_MP, self.MODE_GUILD_ERR_INVALID_HASHTAG, self.MODE_OTHER

        if tw.process_mode != C.MODE_THROUGH:
            text = self._assemble_text(tw)
            self.api.update_status(status=text, in_reply_to_status_id=tw.tweet_id)

        return tw

    def _pre_process(self, status):
        hashtags = list(map(self._convert_str_zen_to_han, self._extract_hashtags_from_status_as_list(status)))
        mention_ids = self._extract_mentions_from_status_as_list(status)
        photo_urls = self._extract_photourls_from_status_as_list(status)
        if len(hashtags) != 0:
            logging.info('hashtag：{}'.format(hashtags))
        if len(mention_ids) != 0:
            logging.info('mention_ids：{}'.format(mention_ids))
        if len(photo_urls) != 0:
            logging.info('photo_urls：{}'.format(photo_urls))
        logging.info('tweet：{}'.format(status.text))

        stage = None
        next_stage = None
        mode = 'b'
        for hashtag in hashtags:
            if hashtag in C.hashtag_corr_stage_dic.keys():
                if stage is None:
                    stage = C.hashtag_corr_stage_dic[hashtag]
                elif next_stage is None:
                    next_stage = C.hashtag_corr_stage_dic[hashtag]
            if hashtag in C.hashtag_corr_mode_dic.keys():
                mode = C.hashtag_corr_mode_dic[hashtag]

        # comment outed parameters will be populated in subsequent.
        tw = Tweet()
        tw.status = status
        # tw.process_mode
        tw.name = status.author.name
        tw.photo_urls = photo_urls
        # tw.photos
        # tw.photo_classes
        tw.rec_exists = None
        # tw.prev_final_score
        tw.mention_ids = mention_ids
        # tw.sfq
        # tw.escr_dict
        tw.next_stage = next_stage
        # tw.best_scores_list
        # tw.std_scores_dict
        tw.user_id = status.author.id
        tw.meta_ids_name = stage
        tw.stage_mode = mode
        tw.screen_name = status.author.screen_name
        tw.tweet_id = status.id
        tw.post_date = status.created_at.date()
        tw.hash_tags = hashtags
        # tw.final_score
        # tw.total_score
        # tw.total_score_probas
        tw.post_datetime = status.created_at
        tw.text = status.text
        # tw.is_score_edited
        # tw.is_valid_data

        return tw

    """
    tool func
        common func, can be called everywhere
    """
    def _check_reply_or_mention_to_me(self, status):
        return self.me.id in MyStreamListener._extract_mentions_from_status_as_list(status)

    def _check_reply_to_my_tweet(self, status):
        return True if self.me.id == status.in_reply_to_user_id and\
                       status.in_reply_to_status_id is not None else False

    def _decision_process_mode_with_photos(self, tw):
        process_mode = C.MODE_OTHER
        if tw.meta_ids_name is not None:
            if 'guild_battle' in tw.photo_classes and 'melonpan' in tw.photo_classes:
                process_mode = C.MODE_HMHM
            elif 'guild_battle' in tw.photo_classes:
                process_mode = C.MODE_GUILD
            elif 'melonpan' in tw.photo_classes:
                process_mode = C.MODE_MP
            else:
                process_mode = C.MODE_OTHER
        elif tw.meta_ids_name is None:
            if 'guild_battle' in tw.photo_classes:
                process_mode = C.MODE_GUILD_ERR_INVALID_HASHTAG
            elif 'melonpan' in tw.photo_classes:
                process_mode = C.MODE_MP
            else:
                process_mode = C.MODE_OTHER

        return process_mode

    def _decision_process_mode_in_reply_my_tweet(self, tw):
        process_mode = C.MODE_THROUGH
        if re.match(u".*訂正.*", tw.text, re.U):
            match_str = re.findall(r"\d+", tw.text, re.U)
            if len(match_str) == 1:
                process_mode = C.MODE_MOD
            else:
                process_mode = C.MODE_MOD_UNIDENTIFY_SCORE
        elif re.match(u".*(取り消し|取消|削除).*", tw.text, re.U):
            process_mode = C.MODE_DELETE
        elif tw.meta_ids_name is not None:
            process_mode = C.MODE_ANOTHER_STAGE_ESTIMATE

        return process_mode

    def _analyse_guild_battle(self, tw):
        db = EurekaDbAccessor()
        db.prepare_connect(cf=self.dbcf)

        # check_prev_data
        tw.prev_final_score, tw.rec_exists = db.select_prev_final_score(tw)

        # estimate digit(this_score)
        sid = f"{tw.meta_ids_name}_{tw.stage_mode}"
        proc_images = []
        for i in np.where(np.array(tw.photo_classes) == 'guild_battle')[0]:
            proc_images.append(tw.photos[i])
        scores, probas = MyStreamListener._ocr_score(proc_images)
        if len(probas) ==0 or np.mean(probas) < 0.8:
            tw.process_mode = C.MODE_GUILD_ERR_INVALID_PHOTO
            return tw

        tw.final_score = scores[0]
        tw.total_score = scores[0]
        tw.total_score_probas = probas
        logging.info('{}: {}'.format(tw.photo_urls, scores))

        # estimate_score(other_stage)
        tw.sfq, tw.escr_dict = MyStreamListener._estimate_scores(sid, tw.final_score)
        if tw.next_stage is None:
            tw.next_stage = self._estimate_next_stage(tw)
        if tw.sfq < 0.000001:
            tw.process_mode = C.MODE_GUILD_ERR_ESTIMATE_SCORE
            return tw

        # save
        db.upsert_result(tw)

        return tw

    def _assemble_text(self, tw):
        text = ''
        if tw.process_mode in (C.MODE_GUILD, C.MODE_HMHM):
            text = self.serif_dict[tw.process_mode]["score"].format(tw.screen_name, tw.final_score)
            if tw.sfq <= 0.5:
                text += self.serif_dict[tw.process_mode]["sfq"].format(self._cut_off_sfq(tw.sfq*100))
            if tw.prev_final_score != 0:
                text += self.serif_dict[tw.process_mode]["prev_score"].format(tw.prev_final_score)
            text += self.serif_dict[tw.process_mode]["estimate_score"]\
                .format(tw.next_stage,
                        self._convert_unit_of_score_to_k(tw.escr_dict[f"{tw.next_stage}_b"], k=True),
                        self._convert_unit_of_score_to_k(tw.escr_dict[f"{tw.next_stage}_n"], k=True, cap=95000)
                        )
            text += random.choice(self.serif_dict["eos"]["tweet_list"]).format(tw.name)
        elif tw.process_mode == C.MODE_MOD:
            text = self.serif_dict[tw.process_mode]["score"].format(tw.screen_name, tw.final_score)
            if tw.sfq <= 0.5:
                text += self.serif_dict["guild_battle"]["sfq"].format(self._cut_off_sfq(tw.sfq*100))
            text += self.serif_dict["guild_battle"]["estimate_score"]\
                .format(tw.next_stage,
                        self._convert_unit_of_score_to_k(tw.escr_dict[f"{tw.next_stage}_b"], k=True),
                        self._convert_unit_of_score_to_k(tw.escr_dict[f"{tw.next_stage}_n"], k=True, cap=95000)
                        )
            text += random.choice(self.serif_dict["eos"]["tweet_list"]).format(tw.name)
        elif tw.process_mode == C.MODE_ANOTHER_STAGE_ESTIMATE:
            text = self.serif_dict[tw.process_mode]["estimate_score"]\
                .format(tw.screen_name,
                        tw.next_stage,
                        self._convert_unit_of_score_to_k(tw.escr_dict[f"{tw.next_stage}_b"], k=True),
                        self._convert_unit_of_score_to_k(tw.escr_dict[f"{tw.next_stage}_n"], k=True, cap=95000)
                        )
        elif tw.process_mode == C.MODE_BEST_SCORE:
            text = self.serif_dict[tw.process_mode]["score_start"].format(tw.screen_name)
            for i, (key, value) in enumerate(C.hashtag_corr_stage_short_dic.items()):
                bs = None
                be = None
                ns = None
                ne = None
                for bscr_dict in tw.best_scores_list:
                    if value == bscr_dict['meta_ids_name']:
                        if 'b' == bscr_dict['stage_mode']:
                            bs = bscr_dict['final_score']
                            be = bscr_dict['is_score_edited']
                        elif 'n' == bscr_dict['stage_mode']:
                            ns = bscr_dict['final_score']
                            ne = bscr_dict['is_score_edited']
                text += "{}:{}{}/{}{}".format(key,
                                              self._convert_unit_of_score_to_k(bs),
                                              '*' if be == '1' else '',
                                              self._convert_unit_of_score_to_k(ns),
                                              '*' if ne == '1' else '')
                if i + 1 < len(C.hashtag_corr_stage_short_dic.items()):
                    text += '|'
            text += self.serif_dict[tw.process_mode]["score_end"]
        elif tw.process_mode == C.MODE_STD_SCORE:
            text = self.serif_dict[tw.process_mode]["score_start"].format(tw.screen_name)
            for i, (key, value) in enumerate(C.hashtag_corr_stage_short_dic.items()):
                bs = tw.std_scores_dict.get(f"{value}_b")
                ns = tw.std_scores_dict.get(f"{value}_n")
                text += "{}:{}{}/{}{}".format(key,
                                              bs if bs is not None else '-',
                                              '*' if bs is not None and
                                                     tw.best_scores_dict['is_score_edited'][f"{value}_b"] == '1'
                                              else '',
                                              ns if ns is not None else '-',
                                              '*' if ns is not None and
                                                     tw.best_scores_dict['is_score_edited'][f"{value}_n"] == '1'
                                              else '')
                if i + 1 < len(C.hashtag_corr_stage_short_dic.items()):
                    text += '|'
            text += self.serif_dict[tw.process_mode]["score_end"]
        elif tw.process_mode in (C.MODE_GUILD_ERR_INVALID_HASHTAG, C.MODE_GUILD_ERR_INVALID_PHOTO,
                                 C.MODE_GUILD_ERR_ESTIMATE_SCORE, C.MODE_MOD_UNIDENTIFY_SCORE,
                                 C.MODE_MOD_RECORD_NOT_FOUND,
                                 C.MODE_DELETE, C.MODE_MP, C.MODE_OTHER):
            text = random.choice(self.serif_dict[tw.process_mode]["tweet_list"]).format(tw.screen_name)
        elif tw.process_mode == C.MODE_THROUGH:
            pass

        return text

    @staticmethod
    def _extract_mentions_from_status_as_list(status):
        return [hash_dic['id'] for hash_dic in status.entities['user_mentions']]

    @staticmethod
    def _extract_hashtags_from_status_as_list(status):
        return [hash_dic['text'] for hash_dic in status.entities['hashtags']]

    @staticmethod
    def _extract_photourls_from_status_as_list(status):
        photo_urls = []
        if hasattr(status, 'extended_entities'):
            for media_dic in status.extended_entities['media']:
                if media_dic['type'] == 'photo':
                    photo_urls.append(media_dic['media_url'])
        return photo_urls

    @staticmethod
    def _contains_hashtags_stage(status):
        stage_contains = False
        for hashtag in MyStreamListener._extract_hashtags_from_status_as_list(status):
            if hashtag in C.hashtag_corr_stage_dic.keys():
                stage_contains = True
        return stage_contains

    @staticmethod
    def _estimate_next_stage(tw):
        # tw_weekday = tw.post_datetime.weekday()
        # tw_before_noon = tw.post_datetime.hour < 12
        # tw_before_night = 12 <= tw.post_datetime.hour < 22
        # workday = [0, 1, 2, 3, 4]
        # holiday = [5, 6]

        next_stage = C.list_stage_workday[0]
        if tw.meta_ids_name in C.list_stage_workday:
            for stage in C.order_stage_workday:
                if tw.meta_ids_name == stage:
                    break
            next_stage = next(C.order_stage_workday)
        elif tw.meta_ids_name in C.list_stage_holiday:
            for stage in C.order_stage_holiday:
                if tw.meta_ids_name == stage:
                    break
            next_stage = next(C.order_stage_holiday)

        return next_stage

    @staticmethod
    def _convert_unit_of_score_to_k(score, k=False, cap=None):
        cvtd_scr = '-'
        if score is not None:
            if cap is not None and score > cap:
                cvtd_scr = 'カンスト'
            elif score > 1000:
                cvtd_scr = "{}{}".format(round(score // 1000), 'k' if k else '')
        return cvtd_scr

    @staticmethod
    def _cut_off_sfq(sfq, scale_list=np.array([50, 40, 30, 25, 20, 15, 10, 8, 6, 5, 4, 2, 1, 0.5, 0.1, 0.05, 0.01])):
        diff = scale_list - sfq
        abs_diff_min_index = np.argmin(abs(diff))
        return scale_list[abs_diff_min_index - 1] if diff[abs_diff_min_index] < 0 else scale_list[abs_diff_min_index]

    @staticmethod
    def _http_request_photos(urls):
        photos = []
        for url in urls:
            try:
                res = get(url)
                content = res.content
                if 'image' in res.headers["content-type"]:
                    photo = MyStreamListener._convert_raw_photo(content)
                    photos.append(photo)
                else:
                    logging.info("non-image Content-Type:{}".format(res.headers["content-type"]))
            except RequestException as re:
                logging.error('requests error(url:{}) :{}'.format(url, str(re)))

        return photos

    @staticmethod
    def _convert_str_zen_to_han(str):
        return unicodedata.normalize('NFKC', str)  # 'NFKD'だとひらがなカタカナ連結してくれないのよ

    @staticmethod
    def _convert_raw_photo(raw_photo):
        return cv2.imdecode(np.frombuffer(raw_photo, dtype=np.uint8), cv2.cv2.IMREAD_COLOR)

    @staticmethod
    def _ocr_score(imgs):
        scores, probas = [], []
        imgs = clip_caputure(imgs)
        imgs = ajust_capture(imgs)
        for img in imgs:
            score, _, _, proba_by_digit = ocr_total_score_cnn([img], MyStreamListener.digit_estimator)
            scores.append(score)
            probas.append(proba_by_digit)
        return scores, probas

    @staticmethod
    def _estimate_scores(sid, bscore):
        return MyStreamListener.score_estimator.estimate_score(sid, bscore)  # sfq, escr_dict

    @staticmethod
    def _calculate_standard_scores(bscr_list):
        return MyStreamListener.score_estimator.calculate_standard_score(bscr_list)  # std_dict

    @staticmethod
    def _classify_images(photos):
        samples = MyStreamListener.melonpan_classifier.sample_image(
            photos,
            resized_shape=(MyStreamListener.melonpan_classifier.input_x,
                           MyStreamListener.melonpan_classifier.input_y),
            normalization=True)
        return MyStreamListener.melonpan_classifier.classify(np.array(samples))  # y, probas


def run_stream(api, stream, config):
    while True:
        try:
            stream.userstream()
        except KeyboardInterrupt as ek:
            exit(1)
        except (Timeout, SSLError) as en:
            retry_count = 0
            logging.warning('stream closed')
            while retry_count < 3:
                time.sleep(1)  # wait a minute.
                logging.warning('retry connection: {}'.format(retry_count))
                retry_count += 1
                try:
                    stream = create_stream(api, config)
                except (Timeout, SSLError) as en:
                    continue
                except Exception as eo:
                    logging.error('unexpected error occur on retry:{:s}'.format(eo))
                    exit(1)
            if stream is None:
                logging.error('retry limit exceeded')
                exit(1)
            else:
                continue
        except tweepy.TweepError as te:
            logging.error('tweep error occur:{:s}'.format(te))
        except Exception as eo:
            logging.error('unexpected error occur:{:s}'.format(eo))
            # exit(1)
        # finally:
        #     if stream is not None:
        #         stream.disconnect()


def authenticate(config):
    consumer_key = config.get("auth", "consumer_key")
    consumer_secret = config.get("auth", "consumer_secret")
    access_token = config.get("auth", "access_token")
    acces_secret = config.get("auth", "acces_secret")
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, acces_secret)

    return tweepy.API(auth)


def create_stream(api, config):
    stream_listener = MyStreamListener(
        api,
        config.get("path", "CKPT_DATA_DIR_TOTAL_SCORE_CLFR"),
        config.get("path", "WEIGHT_DIR_MELONPAN_CLFR"),
        config.get("path", "DB_CONFIG_INI"),
        config.get("path", "SERIF_FILE")
    )

    return tweepy.Stream(auth=api.auth, listener=stream_listener)


if __name__ == '__main__':
    main()
