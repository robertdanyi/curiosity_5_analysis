#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Only works if there's 2 trials altogether
"""


import datetime
import os
import pandas as pd
from constants import DIR


date = str(datetime.datetime.today().date())
dir_name = os.path.join(DIR, "tables", date)
output_excel = os.path.join(dir_name, "curiosity_LT_aggregated_{0}.xlsx".format(date))

def aggregate_data(ord_dict):
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
    
    v_col =  test_cols.pop(-1) # "valid" column
    
    df_int = pd.DataFrame(columns=test_cols+gaze_cols, index=ord_dict.keys())
    df_int.index.name = "subject"
    df_bor = pd.DataFrame(columns=test_cols+gaze_cols, index=ord_dict.keys())
    df_bor.index.name = "subject"

    for key, value in ord_dict.items():
        
        test_results_df = value[0]
        gaze_results_df = value[1]
        
        for i in test_results_df.index:
            if test_results_df.loc[i,v_col]: # if valid 
                df_int.loc[key, test_cols] = test_results_df.loc[i, test_cols]
                df_int.loc[key, gaze_cols] = gaze_results_df.loc[i, gaze_cols]
        
    # add gaze_on_target column and means row, then round up
    df_int = (
            df_int
            .assign(gaze_on_target=df_int.apply(calculate_target_first_gaze, target="int", axis=1))
            .append(df_int.mean(axis=0, numeric_only=None)
                    .rename("mean"))
            .applymap(round_numbers)
            )
    
    df_bor = (
            (df_bor
            .assign(gaze_on_target=df_bor.apply(calculate_target_first_gaze, target="bor", axis=1)))
            .append(df_bor.mean(axis=0, numeric_only=None)
                    .rename("mean"))
            .applymap(round_numbers)
            )
    
    df_int.to_excel(os.path.join(dir_name, "Familiar_label_trial_results_{0}.xlsx".format(date)))
    df_bor.to_excel(os.path.join(dir_name, "Novel_label_trial_results_{0}.xlsx".format(date)))
    print("Aggregated data are saved to excel files.")
    
    
def round_numbers(x):

    if isinstance(x, (float, complex)):
        return round(float(x),3)
    else:
        return x
    
    
def calculate_target_first_gaze(row, target=None):
    
    if not row["1st gaze object"]:
        return "No response"
    
    if str(row["1st gaze object"]).lower() == target:
        return 1
    else:
        return 0
    
    
    
        
        
        
        
    