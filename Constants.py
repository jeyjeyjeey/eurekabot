# coding: utf-8
import copy
from itertools import cycle
from collections import OrderedDict

MODE_GUILD = 'guild_battle'
MODE_MOD = 'guild_mod'
MODE_DELETE = 'guild_delete'
MODE_WAIRO_TYOUDAI = 'wairo_tyoudai'
MODE_WAIRO = 'wairo'
MODE_BEST_SCORE = 'best_score'
MODE_STD_SCORE = 'standard_score'
MODE_MP = 'melonpan'
MODE_OTHER = 'other'
MODE_ANOTHER_STAGE_ESTIMATE = 'another_stage_estimate'
MODE_GUILD_ERR_INVALID_HASHTAG = 'guild_err_invalid_hashtag'
MODE_GUILD_ERR_INVALID_PHOTO = 'guild_err_invalid_photo'
MODE_MOD_DEL_ERR_TWEET_NOT_FOUND = 'guild_mod_del_err_tweet_not_found'
MODE_MOD_DEL_ERR_MISTAKE_REPLY = 'guild_mod_del_err_mistake_reply'
MODE_MOD_ERR_UNIDENTIFY_SCORE = 'guild_mod_err_unidentify_score'
MODE_MOD_ERR_RECORD_NOT_FOUND = 'guild_mod_err_record_not_found'
MODE_DEL_ERR_RECORD_NOT_FOUND = 'guild_del_err_record_not_found'
MODE_THROUGH = 'through'

MODE_GUILD_ERR_ESTIMATE_SCORE = 'guild_err_estimate_score'
MODE_HMHM = 'hamuhamu'

DB_RECORD_INSERT = 'i'
DB_RECORD_UPDATE = 'u'
DB_RECORD_NOT_UPDATE = 'nu'
DB_RECORD_DELETE = 'd'

HASHTAG_BEST_SCORE_HIRAKANA = 'ゴ魔乙ギルバト自己べ'
HASHTAG_BEST_SCORE_KATAKANA = 'ゴ魔乙ギルバト自己ベ'
HASHTAG_BEST_SCORE_KATAKANA_FULL = 'ゴ魔乙ギルバト自己ベスト'
HASHTAG_BEST_SCORE_SET = {HASHTAG_BEST_SCORE_HIRAKANA, HASHTAG_BEST_SCORE_KATAKANA, HASHTAG_BEST_SCORE_KATAKANA_FULL}
HASHTAG_BEST_SCORE = 'ゴ魔乙ギルバト自己べ'
HASHTAG_STD_SCORE = 'ゴ魔乙ギルバト通知表'

hashtag_corr_stage_full_dic = OrderedDict({
    '水有利1': '水有利1', '火有利1': '火有利1', '闇有利2': '闇有利2', '風有利1': '風有利1', '混合火1': '混合火1',
    '火有利2': '火有利2', '光有利2': '光有利2',
    '闇有利1': '闇有利1', '水有利2': '水有利2', '光有利1': '光有利1', '風有利2': '風有利2', '混合闇1': '混合闇1'
})
hashtag_corr_stage_short_dic = OrderedDict({
    '水1': '水有利1', '火1': '火有利1', '闇2': '闇有利2', '風1': '風有利1', '混火': '混合火1',
    '火2': '火有利2', '光2': '光有利2',
    '闇1': '闇有利1', '水2': '水有利2', '光1': '光有利1', '風2': '風有利2', '混闇': '混合闇1'
})
hashtag_corr_stage_dic = copy.deepcopy(hashtag_corr_stage_full_dic)
hashtag_corr_stage_dic.update(hashtag_corr_stage_short_dic)
hashtag_corr_stage_short_inv_dic = {value: key for key, value in hashtag_corr_stage_short_dic.items()}

hashtag_corr_stage_full_workday_st_stage = '水有利1'
hashtag_corr_stage_workday_st_ind = \
    list(hashtag_corr_stage_full_dic.keys()).index(hashtag_corr_stage_full_workday_st_stage)
hashtag_corr_stage_full_holiday_st_stage = '闇有利1'
hashtag_corr_stage_holiday_st_ind = \
    list(hashtag_corr_stage_full_dic.keys()).index(hashtag_corr_stage_full_holiday_st_stage)

hashtag_corr_mode_dic = {'ブレイク': 'b', '非ブレ': 'n'}
hashtag_corr_mode_inv_dic = {value: key for key, value in hashtag_corr_mode_dic.items()}

list_stage_workday = ['水有利1', '火有利1', '闇有利2', '風有利1', '混合火1', '火有利2', '光有利2']
list_stage_holiday = ['闇有利1', '水有利2', '光有利1', '風有利2', '混合闇1']
order_stage_workday = cycle(list_stage_workday)
order_stage_holiday = cycle(list_stage_holiday)
