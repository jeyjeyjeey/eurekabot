# coding: utf-8

import logging

logger = logging.getLogger(__name__)


class Tweet:
    def __init__(self):
        self.status = None  # status object
        self.process_mode = None
        self.__name = str()
        self.photo_urls = list()
        self.photos = list()
        self.photo_classes = list()
        self.rec_exists = None  # bool()
        self.prev_final_score = int()
        self.mention_ids = list()
        self.sfq = float()
        self.escr_dict = dict()
        self.__best_scores_list = list()
        self.best_scores_dict = dict()
        self.std_scores_dict = dict()
        self.next_stage = str()
        self.user_id = str()
        self.meta_ids_name = str()
        self.stage_mode = str()
        self.screen_name = str()
        self.tweet_id = str()
        self.post_date = str()
        self.hash_tags = list()
        self.final_score = int()
        self.total_score = int()
        self.total_score_probas = list()
        self.estimate_score_raw = dict()
        self.post_datetime = str()
        self.text = str()
        self.is_score_edited = str('0')
        self.is_valid_data = str('0')

    # since other properties are simple, they are omitted

    @property
    def best_scores_list(self):
        return self.__best_scores_list

    @best_scores_list.setter
    def best_scores_list(self, list_has_dict):
        self.__best_scores_list = list_has_dict
        if list_has_dict is not None and len(list_has_dict) != 0:
            try:
                proc_keys_list = list(list_has_dict[0].keys())
                [proc_keys_list.remove(id_key) for id_key in ('meta_ids_name', 'stage_mode')]
                best_scores_dict = {}
                for proc_key in proc_keys_list:
                    for_each_key_dict = {}
                    for dict in list_has_dict:
                        sid = "{}_{}".format(dict['meta_ids_name'], dict['stage_mode'])
                        for_each_key_dict[sid] = dict[proc_key]
                    best_scores_dict[proc_key] = for_each_key_dict
            except Exception as e:
                logger.error('best_scores_list is unexpected structure: {}'.format(list_has_dict))
                raise
            self.best_scores_dict = best_scores_dict

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value):
        self.__name = f"{value[:20]}..." if len(value) > 20 else value
