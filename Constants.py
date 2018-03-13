# coding: utf-8
import copy
from itertools import cycle

MODE_GUILD = 'guild_battle'
MODE_HMHM = 'hamuhamu'
MODE_MP = 'melonpan'
MODE_BEST_SCORE = 'best_score'
MODE_STD_SCORE = 'standard_score'
MODE_OTHER = 'other'
MODE_MOD = 'guild_mod'
MODE_DELETE = 'guild_delete'
MODE_ANOTHER_STAGE_ESTIMATE = 'another_stage_estimate'
MODE_GUILD_ERR_INVALID_HASHTAG = 'guild_err_invalid_hashtag'
MODE_GUILD_ERR_INVALID_PHOTO = 'guild_err_invalid_photo'
MODE_GUILD_ERR_ESTIMATE_SCORE = 'guild_err_estimate_score'
MODE_MOD_UNIDENTIFY_SCORE = 'guild_mod_err_unidentify_score'
MODE_MOD_RECORD_NOT_FOUND = 'guild_mod_err_record_not_found'
MODE_MOD_TWEET_NOT_FOUND = 'guild_mod_err_tweet_not_found'
MODE_THROUGH = 'through'

HASHTAG_BEST_SCORE = 'ゴ魔乙ギルバト自己べ'
HASHTAG_STD_SCORE = 'ゴ魔乙ギルバト通知表'

hashtag_corr_stage_full_dic = {
    '火有利1': '火有利1', '水有利1': '水有利1', '風有利1': '風有利1', '混合火1': '混合火1',
    '闇有利1': '闇有利1', '光有利1': '光有利1', '混合闇1': '混合闇1',
    '水有利2': '水有利2', '風有利2': '風有利2',
    '闇有利2': '闇有利2', '光有利2': '光有利2', '火有利2': '火有利2',
}
hashtag_corr_stage_short_dic = {
    '火1': '火有利1', '水1': '水有利1', '風1': '風有利1', '混火': '混合火1',
    '闇1': '闇有利1', '光1': '光有利1', '混闇': '混合闇1',
    '水2': '水有利2', '風2': '風有利2',
    '闇2': '闇有利2', '光2': '光有利2', '火2': '火有利2',
}
hashtag_corr_stage_dic = copy.deepcopy(hashtag_corr_stage_full_dic)
hashtag_corr_stage_dic.update(hashtag_corr_stage_short_dic)
hashtag_corr_stage_short_inv_dic = {value: key for key, value in hashtag_corr_stage_short_dic.items()}
hashtag_corr_mode_dic = {'ブレイク': 'b', '非ブレ': 'n'}
hashtag_corr_mode_inv_dic = {value: key for key, value in hashtag_corr_mode_dic.items()}

list_stage_workday = ['水有利1', '火有利1', '闇有利2', '風有利1', '混合火1', '火有利2', '光有利2']
list_stage_holiday = ['闇有利1', '水有利2', '光有利1', '風有利2', '混合闇1']
order_stage_workday = cycle(list_stage_workday)
order_stage_holiday = cycle(list_stage_holiday)
