# coding: utf-8
import logging
import numpy as np
from scipy.stats import johnsonsu
import pandas as pd

from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, bindparam

from gmot.data.DbAccessor import DBAccessor

logger = logging.getLogger(__name__)


def main():
    se = ScoreEstimator()
    se.prepare()
    sfq, escr_dic = se.estimate_score('光有利2_b', 190000)
    print(escr_dic)
    print(f"上位{sfq*100:0.2f}％に位置")


class ScoreEstimator:

    sql_stat = text("""
    select
        gb_posts.meta_ids_name,
        gb_posts.stage_mode
    from
        gb_posts
    where
        gb_posts.is_valid_data = '0'
    group by
        gb_posts.meta_ids_name,
        gb_posts.stage_mode
    order by
        gb_posts.stage_mode,
        gb_posts.meta_ids_name
        """)

    sql_sample = text("""
    select
        gb_posts.user_id,
        gb_posts.final_score
    from
        gb_posts,
        (select
            user_id,
            MAX(final_score) as best_score
        from
            gb_posts
        where
            meta_ids_name = :stag and 
            stage_mode = :mode and 
            is_valid_data = '0'
        group by
            user_id) max_post
    where
        gb_posts.user_id = max_post.user_id and
        gb_posts.final_score = max_post.best_score and
        gb_posts.meta_ids_name = :stag and
        gb_posts.is_valid_data = '0'
    order by
        gb_posts.final_score desc
        """, bindparams=[bindparam('stag'), bindparam('mode')])

    def __init__(self, db_cf='../gmot/gb/config.ini'):
        self.__list_stage_id = list()
        self.__df_sample_by_user = None
        self.__rvs = dict()
        self.__db_cf = db_cf

    def prepare(self):
        if len(self.__rvs) != 0:
            return self
        self.__df_sample_by_user, self.__list_stage_id = self._get_stat_scores()
        self.__df_sample_by_user = self._cleanse_data(self.__df_sample_by_user, self.__list_stage_id)
        self.__rvs = self._define_distribution(self.__df_sample_by_user, self.__list_stage_id)
        logger.debug('mvsk:{}'.format({sid: rvs.stats(moments='mvsk') for sid, rvs in self.__rvs.items()}))
        return self

    def estimate_score(self, sid, bscr):
        if len(self.__rvs) == 0:
            self.prepare()
        if not isinstance(bscr, int):
            bscr = int(bscr)
        sfq = self.__rvs[sid].sf(x=bscr)
        escr_dic = {sid: np.round(self.__rvs[sid].isf(q=sfq), 0).astype(np.int64) for sid in self.__list_stage_id}
        logger.debug(f"sfq:{sfq}, escr_dic:{escr_dic}")
        return sfq, escr_dic

    def calculate_standard_score(self, bscr_list):
        std_scr_dict = {}
        for bscr_dict in bscr_list:
            sid = f"{bscr_dict['meta_ids_name']}_{bscr_dict['stage_mode']}"
            std_scr = ((10 * (bscr_dict['final_score'] - self.__rvs[sid].mean())) / self.__rvs[sid].std()) + 50
            std_scr_dict[sid] = round(std_scr, 1)
        return std_scr_dict

    def _get_stat_scores(self):
        db = DBAccessor()
        db.prepare_connect(cf=self.__db_cf, echo=False)

        session_maker = sessionmaker(bind=db.engine)
        session = session_maker()

        rs_stat = session.execute(self.sql_stat).fetchall()
        df_stat = pd.DataFrame(data=rs_stat, columns=['stag', 'smode'])

        df_stage = df_stat[['stag', 'smode']]
        list_stage = [(df_stage.iloc[rowi].stag, df_stage.iloc[rowi].smode) for rowi in df_stage.T]
        list_stage_id = [f"{stag}_{smode}" for stag, smode in list_stage]

        df_sample_by_user = None
        for stag, smode in list_stage:
            rs_sample = session.execute(self.sql_sample, {'stag': stag, 'mode': smode}).fetchall()
            df_tmp = pd.DataFrame(data=rs_sample, columns=['user_id', f"{stag}_{smode}"]) \
                .astype({'user_id': np.str, f"{stag}_{smode}": np.int64})
            if df_sample_by_user is not None:
                df_sample_by_user = pd.merge(df_sample_by_user, df_tmp, on='user_id', how='outer')
            else:
                df_sample_by_user = df_tmp

        session.commit()
        session.close()

        return df_sample_by_user, list_stage_id

    def _cleanse_data(self, df_sample_by_user, list_stage_id):
        for sid in list_stage_id:
            ex_ind = self._exclude_outliers_in_df(df_sample_by_user, sid, delf=False)
            df_sample_by_user.loc[ex_ind, sid] = np.nan

        return df_sample_by_user

    @staticmethod
    def _define_distribution(df_sample_byuser, list_stage_id):
        return {sid: johnsonsu(*johnsonsu.fit(df_sample_byuser[sid].dropna()))
                for i, sid in enumerate(list_stage_id)}

    @staticmethod
    def _exclude_outliers_in_df(df, col, delf=False):
        Q1 = np.percentile(df[col].dropna(), 25)  # 1st quartile (25%)
        Q3 = np.percentile(df[col].dropna(), 75)  # 3rd quartile (75%)
        IQR = Q3 - Q1  # Interquartile range (IQR)
        outlier_step = 1.5 * IQR
        outlier_step_min = Q1 - outlier_step
        outlier_step_max = Q3 + outlier_step

        outlier_indices = df[(df[col] < outlier_step_min) | (df[col] > outlier_step_max)].index
        return df.drop(outlier_indices, axis=0).reset_index(drop=True) if delf else outlier_indices


if __name__ == '__main__':
    main()
