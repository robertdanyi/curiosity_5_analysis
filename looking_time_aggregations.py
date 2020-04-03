#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Only works if there's 2 trials altogether
"""


import datetime
import os
import pandas as pd
import swifter
from constants import DIR


date = str(datetime.datetime.today().date())
dir_name = os.path.join(DIR, "tables", date)
output_excel = os.path.join(dir_name, "curiosity_LT_aggregated_{0}.xlsx".format(date))

def aggregate_data(ord_dict, timing):
    """
    Aggregates data from ord_dict
    ord_dict: dictionary with 
        key: subject number 
        value: a list of test results dataframe and gaze results dataframe 
    """
    # get columns to use
    df_t, df_g = ord_dict[list(ord_dict.keys())[0]] # first subject's list of dfs
    test_cols = list(df_t.columns)[4:]
    gaze_cols = list(df_g.columns)
    
    validity_col =  test_cols.pop(-1)
    
    df_int = pd.DataFrame(columns=test_cols+gaze_cols, index=ord_dict.keys())
    df_int.index.name = "subject"
    df_bor = pd.DataFrame(columns=test_cols+gaze_cols, index=ord_dict.keys())
    df_bor.index.name = "subject"

    for key, value in ord_dict.items():
        
        test_results_df = value[0]
        gaze_results_df = value[1]
        
        for i in test_results_df.index:
            if test_results_df.loc[i,validity_col]: # if valid
                if i%2 == 0:
                    df_int.loc[key, test_cols] = test_results_df.loc[i, test_cols]
                    df_int.loc[key, gaze_cols] = gaze_results_df.loc[i, gaze_cols]
                else:
                    df_bor.loc[key, test_cols] = test_results_df.loc[i, test_cols]
                    df_bor.loc[key, gaze_cols] = gaze_results_df.loc[i, gaze_cols]
        
    # add gaze_on_target column and means row, then round up
    df_int = (
            df_int
            .assign(gaze_on_target=df_int
                    .swifter.progress_bar(False).apply(_calculate_target_first_gaze, target="int", axis=1))
            .append(df_int.mean(axis=0, numeric_only=None)
                    .rename("mean"))
            .applymap(_round_numbers)
            )
    
    df_bor = (
            (df_bor
            .assign(gaze_on_target=df_bor
                    .swifter.progress_bar(False).apply(_calculate_target_first_gaze, target="bor", axis=1)))
            .append(df_bor.mean(axis=0, numeric_only=None)
                    .rename("mean"))
            .applymap(_round_numbers)
            )
    
    df_int.to_excel(os.path.join(dir_name, f"Familiar_label_trial_results_{timing}_{date}.xlsx"))
    df_bor.to_excel(os.path.join(dir_name, f"Novel_label_trial_results_{timing}_{date}.xlsx"))
    print("Aggregated data are saved to excel files.")
    
    
def _round_numbers(x):

    if isinstance(x, (float, complex)):
        return round(float(x),3)
    else:
        return x
    
    
def _calculate_target_first_gaze(row, target=None):
    
    first_gaze = row["1st gaze object"]
    if (not first_gaze) or (pd.isna(first_gaze)):
        return "No response"
    
    if str(row["1st gaze object"]).lower() == target:
        return 1
    else:
        return 0
    
    
    
        
        
        
        
    