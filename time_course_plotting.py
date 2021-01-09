#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
input:
    - aoi tags for test data to calculate target/distractor look for each timestamp
    - normalised baseline data for interesting and boring objects to be subtracted from target/distractor looks

1.
on test df apply _calculate_target_look

In principle there can be more than one of each kind of trial (familiar or novel)
in that case, average for familiar and novel trials of each subject.

This is only target look at each timestamp, no gaze data is provided. (gaze > 100ms?)
We need to filter out subject trials where there was no gaze response.
We cannot do this from the input data, as it only contains aoi tags.
We need another key:value in the input dicts: responded:yes/no

"""

from __future__ import print_function
from __future__ import division
import pandas as pd
pd.options.mode.chained_assignment = None
import numpy as np
import os
import datetime
import pickle
import swifter

from constants import DIR, ST
import plot_plotly as plot


date = str(datetime.datetime.today().date())

#input
pickle_jar = os.path.join(DIR, "time_course", "pickle")

#output
plots_dir = os.path.join(DIR, "time_course", "plots", f"{date}")
tables_dir_name = os.path.join(DIR, "time_course", "tables", f"{date}")
excelfile = os.path.join(tables_dir_name, f"target_look_dataframes_per_label_{date}.xlsx")
writer = pd.ExcelWriter(excelfile)


def open_pickle():

    tc_dict = {}

    pickle_filename = "tc_dict_4sec_test_2020-07-23"

    with open(os.path.join(pickle_jar, pickle_filename + '.pkl'), 'rb') as f:
        tc_dict = pickle.load(f)

    analyse_time_course(tc_dict)


def analyse_time_course(tc_dict):
    """
    tc_dict: dictionary with following structure:
        key: subj_nr; value: dict
            key: trial nr (0, 2... for familiar trials and 1,3... for novel trials of subject); value: dict
                key: "AOI", value: series of aoi tags for trial
                key: "BL_INT" , value: baseline look on int (scalar)
                key: "BL_BOR", value: baleline look on bor (scalar)
                key: "BL_FAM", value: baseline look on familiar objects
                key: "responded", value: boolean

    tls_per_trials: dict to collect target looks per trial
        keys: 0,1 trials; values: list of subject data series for each trial
    """

    _create_paths([plots_dir, tables_dir_name])

    _do_target_look_calculations(tc_dict, fam=False)

    _do_target_look_calculations(tc_dict, fam=True)


def _do_target_look_calculations(tc_dict, fam):

    tls_per_trials = {nr: [] for nr in [0,1]}

    for subj, subj_dict in tc_dict.items(): # subj_dict = tc_dict[subj]

        subj_data = {} # collect subject data

        for trial_nr, d in subj_dict.items(): # d = tc_dict[subj][trial_nr]

            trial_nr = int(trial_nr)

            if d["responded"]:

                if fam:
                    target, distractor = "fam", None
                    bl_target = d["BL_FAM"]
                else:
                    target, distractor = ("int", "bor") if trial_nr%2==0 else ("bor", "int")
                    # normalise
                    denom = d["BL_INT"] + d["BL_BOR"]
                    bl_target = d["BL_INT"]/denom if trial_nr%2==0 else d["BL_BOR"]/denom

                test_data_series = pd.Series(d["AOI"])

                target_look = (test_data_series
                                    .swifter.progress_bar(False).apply(_calculate_target_look,
                                           target=target,
                                           dist=distractor,
                                           bl_target=bl_target)
                                )

                subj_data[trial_nr] = target_look

        # reduce trials to two by averaging related trials
        if len(list(subj_data.keys())) > 2:
            subj_data = _average_paired_trials(subj_data)

        for n in subj_data.keys():
            tls_per_trials[n].append(subj_data[n]) # append series

    _prep_data_for_plotting(tls_per_trials, fam)


def _calculate_target_look(tag, target, dist, bl_target=0):
    """
    params:
        tag: aoi tag
        target: labeled object: "int" or "bor"
        dist = distractor object or None
        bl_target: baseline value of target

    returns:
        1 or 0 minus the relevant baseline for each gazepoint.
    """

    bl_dist = 1-bl_target

    if dist:
        dist = [dist]
    else:
        dist=["int","bor"]

    if tag.lower() == target:
        return 1 - bl_target
    elif tag.lower() in dist:
        return 0 - bl_dist
    else:
        return np.nan


def _average_paired_trials(subj_trials):
    """
    Averages trial paires for subject (if nr of trials > 2),
    assuming even indexes are familiar label trials, odds are novel label trials

    returns:
        dict with two mean trial values for subject
    """
    keys = list(subj_trials.keys()) #[0,1,2,3]
    familiar_keys = list( filter(lambda x: x%2==0, keys) )
    novel_keys = list( filter(lambda x: x%2==1, keys) )

    familiar_data = [subj_trials[k]["corr_data"] for k in familiar_keys] # list of series
    familiar_data = pd.concat(familiar_data, axis=1)
    mean_fam_data = familiar_data.mean(axis=1)

    novel_data = [subj_trials[k]["corr_data"] for k in novel_keys]
    novel_data = pd.concat(novel_data, axis=1)
    mean_novel_data = novel_data.mean(axis=1)

    return {0:mean_fam_data, 1:mean_novel_data}


def _prep_data_for_plotting(tls_per_trials, fam):
    """
    for plotly
    add columns: SE, time, sample mean, nr_of_datapoints
    """

    for trial_nr in tls_per_trials.keys():

        nr_of_subjects = len(tls_per_trials[trial_nr])
        if nr_of_subjects > 1:
            df_tls = pd.concat(tls_per_trials[trial_nr], axis=1, ignore_index=True)
        else: # for testing on one file
            df_tls = pd.DataFrame(columns=["data", "time"])
            df_tls["data"] = tls_per_trials[trial_nr]

        # add useful columns
        data_cols = df_tls.columns
        df_tls = (df_tls
                .assign(SE = df_tls
                        .swifter.progress_bar(False).apply(_calculate_standard_error, axis=1))
                .assign(time = list(df_tls.index * ST))
                .assign(sample_mean = df_tls.loc[:, data_cols]
                        .mean(axis=1))
                .assign(nr_of_datapoints = df_tls.loc[:, data_cols]
                        .swifter.progress_bar(False).apply(lambda x: x.notna().sum(), axis=1))
                )

        obj = "COMMON objects" if fam else "TARGET object"
        label = "Familiar" if trial_nr==0 else "Novel"

        excelfilename = os.path.join(tables_dir_name, f"Look on {obj}_in_{label}_trials_df.xlsx")

        df_tls.to_excel(excelfilename, sheet_name=label, index=False)

#        plot.plot_plotly1(df_tls, label=label, obj=obj, n=nr_of_subjects)

        plot.plot_plotly2(df_tls, label=label, obj=obj, n=nr_of_subjects)


def _calculate_standard_error(sample):
    """
    a sample: series of data of all subjects at the timepoint
    """
    n = sample.size

    std = sample.std(ddof=1)
    se = std / np.sqrt(n)

    return se


# unused
def _calculate_mean_target_look(sample):
    """
    a sample: series of data of all subjects at the timepoint
    calculates mean of sample target looks at the timepoint;
    returns:
        nan if sample size = 1
        sample mean
    """

    if sample.size < 2:
        return np.nan

    else:
        return sample.mean()


def _create_paths(paths):

    for path in paths:
        try:
            os.makedirs(path)
        except FileExistsError:
            pass


if __name__ == "__main__":
    open_pickle()




