# -*- coding: utf-8 -*-
"""
Plots time course of proportional target looks per trial and per label.
Writes

"""

from __future__ import print_function
from __future__ import division
import pandas as pd
pd.options.mode.chained_assignment = None
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
sns.set(style="darkgrid")
#from scipy import stats
from functools import reduce
import collections
import datetime

import constants_times_5 as c
import reading_and_transformations as rt
import calculations as calc
import t_tests


dt = str(datetime.datetime.today())
date = str(datetime.datetime.today().date())
logfiles = os.path.join(c.DIR, "data_to_read")
tables_dir_name = os.path.join(c.DIR, "time_course", "tables", f"{date}")
try: os.makedirs(tables_dir_name)
except FileExistsError: pass

plots_dirname = os.path.join(c.DIR, "time_course", "plots", f"{date}")
try: os.makedirs(plots_dirname)
except FileExistsError: pass

excelfile1 = os.path.join(tables_dir_name, f"target_look_dataframes_per_trial_{date}.xlsx")
writer1 = pd.ExcelWriter(excelfile1)
excelfile2 = os.path.join(tables_dir_name, f"target_look_dataframes_per_label_{date}.xlsx")
writer2 = pd.ExcelWriter(excelfile2)

# AOI namedtuple
AOI = collections.namedtuple("AOI", "inter, bor, fam1, fam2")

# dict to collect target looks per trial
tls_per_trials = {f"trial_{x}_tls":[] for x in [1,2]}


def main():
    """
    tls_per_trials: dict
        keys: trial_1_tls, trial_2_tls
        values: list of series of target looks

    Returns None
    """

    print("\tTotal number of files: ", len(os.listdir(logfiles)))

    subjects = []

    for log in os.listdir(logfiles):

        # "s08_PJ_f_3-1-2-4_2019-08-12_TOBII_output.tsv"
        print("\nReading file {0}".format(log))

        subj_nr = log.split("_")[0]
        logfilepath = os.path.join(logfiles, log)

        valid_subject = extract_and_transform_subject_data(logfilepath, subj_nr)

        if valid_subject:
            subjects.append(subj_nr)
        print("subjects:", subjects)

    # print("trial 2 tls:\n", tls_per_trials["trial_2_tls"])
    # # plot per trial
    # _plot_per_trial(tls_per_trials)

    print("\n valid subjects: ", subjects)
    # print("\n tls 'other' data:", len(tls_per_trials["trial_2_tls"]))

    # plot per label (1-3, 2-4 trials)
    load_data_per_label(tls_per_trials)


def extract_and_transform_subject_data(logfilepath, subj_nr):
    """
    Loads the logfile to a dataframe.
    Calls validate() on dataframe.
    Calculates the time course data for the test period.

    Parameters
    ----------
    logfilepath : string; path of logfile
    subj_nr : string; the number of the participant

    Returns
    -------
    True if subject data is extracted and valid
    """

    df = rt.read_tsv_file(logfilepath)

    if df is None:
        print("!!!WARNING! The file '{}' is compromised. Please check.".format(os.path.basename(logfilepath)))
        return False

    valid_data = validate(df, subj_nr)
    if not valid_data:
        return False

    df_events, df = valid_data

    test = c.Test_data(df_events)

    # test start event example: "test__int_label_top_right_bitye_STARTS"
    positions_of_int = ["-".join(e.split("_")[-4:-2]) for e in test.start_events]
    test_interesting_positions(positions_of_int)
    print("interesting sides: ", positions_of_int)

    # onscreen looks during 2 tests
    look_on_screen = _calculate_onscreen_gaze(df, test.start_times, test.end_times)

    # baselines = {"int":[], "bor":[]}

    """
    TODO: could separate 'target' for interesting and boring labels.
    1st round of test: target: interesting
    2nd round of test: target boring
    """
    for n in range(len(test.start_events)):

        # Validation 3: ag look and look on screen in test phase
        ag_start = test.ag_start_times[n]

        ag_df = df[(ag_start < df["TimeStamp"]) & (df["TimeStamp"] < ag_start+2000)]
        looked_on_ag = True if ag_df["gazepoints"].apply(_contains, args=(c.AOI_ag,)).sum() > 0 else False

        if not looked_on_ag:
            print("\tWARNING! {0} didn't look at the Attention Getter in test round {1}.--> Invalid trial.".format(subj_nr, n+1))
            continue

        if look_on_screen[n] < 0.5:
            print("\tWARNING! {0} didn't look at the screen long enough in test round {1}.--> Invalid trial.".format(subj_nr, n+1))
            continue

        int_pos = positions_of_int[n]
        # AOIs in round n
        aoi = AOI(inter=c.AOI_dict[int_pos][0],
              bor=c.AOI_dict[int_pos][1],
              fam1=c.AOI_dict[int_pos][2],
              fam2=c.AOI_dict[int_pos][3])

        ### parse baseline in round
        bl_onint, bl_onboring = parse_baseline_data(df, aoi,
                                                start_time=test.bl_start_times[n], end_time=test.ag_start_times[n],
                                                subj_nr=subj_nr)
        # print("bl_start_time, bl_end_time:", test.bl_start_times[n], test.ag_start_times[n])
        # print("bl_onint, bl_onboring:",bl_onint, bl_onboring)


        ### parse test in round
        test_df = rt.assign_aoi_tags(df, test.start_times[n], test.end_times[n], aoi)
        # print("test_df with aoi tags:\n", test_df.head())

        # calculate the time course for the test period
        # could pass n to adjust 'target' to label
        test_df = test_df.assign(target_look = test_df["aoi"].apply(_calculate_target_look, args=(aoi.inter, aoi.bor), baseline=bl_onint).values)
        # print("test_df with target looks:\n", test_df.head())
        # create list from series, then append recreated series to match indices
        target_looks = pd.Series(data=test_df["target_look"].tolist())
        tls_per_trials[f"trial_{n+1}_tls"].append(pd.Series(target_looks))
        # print("\t-> size of test_df.target_look series:", test_df["target_look"].size)

    return True


def check_if_completed(events, subj_nr):

    if c.EXP_COMPLETED not in events:
        print("!! Experiment was NOT COMPLETED.\n!! Subject {0} has no valid data".format(subj_nr))
#        logging.warning("!! Experiment was NOT COMPLETED.\n!! Subject {0} has no valid data".format(subj_nr))
        return False
    else:
        return True


def validate(df, subj_nr):
    """
    The input dataframe (df) is separated to
        an event dataframe
        and a df containing the gazepoints without the events.
    The gazepoints data is interpolated.
    The interpolated subject data is validated against some requirements.
    Check if the subject's data is valid. Is valid if:
        - Average look on screen during known objects demo > 0.6
        - Average look on screen during known objects labeling > 0.6
        - Average look on screen during familiarisation > 0.6
        - Average look on screen during familiarisation labeling > 0.6
    """

    df_events, df = rt.detach_events(df)
    events = df_events["Event"].tolist()

    # Validation 1: if exp was not completed, don't bother
    if not check_if_completed(events, subj_nr):
        return None

    df = rt.interpolate_missing_samples(df)

#    # list of occuring events
    events = df_events["Event"].tolist()

    # Intro objects - look onscreen
    intro = c.Fam_data(df_events)
    intro_onscreens = _calculate_onscreen_gaze(df, intro.start_times, intro.end_times)

    if _average(intro_onscreens) < 0.6:
        print("\tWARNING! Not enough looking time onscreen during intro section")
        return None

    # Intro objects labeling - looking time on screen
    intro_label_onscreens = _calculate_onscreen_gaze(df, intro.label_start_times, intro.label_end_times)

    if _average(intro_label_onscreens) < 0.6:
        print("\tWARNING! Not enough looking time on screen during intro labeling section")
        return None

    ### Familiarisation of new object - looking time on screen and interesting and boring "new" objects -- "n"
    familiarisation = c.Teaching_data(df_events)
    # interesting_sides = [e.split("_")[-1][:-1] for e in events if (e.startswith("Familiarisation_anim"))]
    # print("\tFamiliarisation interesting sides:", interesting_sides)
    fam_onscreens = _calculate_onscreen_gaze(df, familiarisation.start_times, familiarisation.end_times)

    if _average(fam_onscreens) < 0.6:
        print("\tWARNING! Not enough looking time on screen during familiarisation")
        return None


    ### Labeling new objects - looking time on screen - "ln"
    ln_onscreens = _calculate_onscreen_gaze(df, familiarisation.label_start_times, familiarisation.label_end_times)

    if _average(ln_onscreens) < 0.6:
        print("\tWARNING! Not enough looking time on screen during familiarisation labeling")
        return None

    return (df_events, df)


def parse_baseline_data(df, aoi, start_time=None, end_time=None, subj_nr=None):
    """
    Baselines are calculated in proportion to the sum gaze to the interesting, boring
    and familar objects.
    """

    bl_df = rt.assign_aoi_tags(df, start_time, end_time, aoi)
    bl_gaze = calc.collect_gaze(bl_df)
    bl_onint, bl_onboring, _ = bl_gaze.calculate_onobject_gaze()
    # baselines["int"].append(bl_onint)
    # baselines["bor"].append(bl_onboring)

    return bl_onint, bl_onboring


def _plot_per_trial(tls_per_trials):
    """Prepares target looks dataframes for plotting and writing to excel files for each test."""

    for key in tls_per_trials.keys():

        trial_nr = int(key.split("_")[1])
        nr_of_subjects = len(tls_per_trials[key])
        df_tls = pd.concat(tls_per_trials[key], axis=1, ignore_index=True)

        time_frame = list(df_tls.index * 16.7)
        df_tls["time"] = time_frame
        # print("last timestamp in df:", df_tls["time"].tolist()[-1])

        _write_to_excel(df_tls, writer1, key)

        melted_df = pd.melt(df_tls, id_vars=["time"], var_name="subject", value_name="target_look")
        _plot_time_course(melted_df, time_frame, trial_nr=trial_nr, nr=nr_of_subjects)


def load_data_per_label(tls_per_trials):
    """Prepares target looks dataframes for plotting and writing to excel files for each label."""

    # assuming even indexes are interesting trials, odds are boring trials
    # keys: trial_1_tls, trial_2_tls...
    keys = list(tls_per_trials.keys())
    int_keys = [keys[x] for x in range(len(keys)) if x%2==0]
    bor_keys = [keys[x] for x in range(len(keys)) if x%2==1]

    int_series_list = [tls_per_trials[key] for key in int_keys] # list of lists (of series) # now a list of only one list of series
    int_series_list = reduce(lambda x,y:x+y, int_series_list)
    nr_int_trials = len(int_series_list)
    bor_series_list = [tls_per_trials[key] for key in bor_keys]
    bor_series_list = reduce(lambda x,y:x+y, bor_series_list)
    nr_bor_trials = len(bor_series_list)

    df_int = pd.concat(int_series_list, axis=1, ignore_index=True)
    df_other = pd.concat(bor_series_list, axis=1, ignore_index=True)

    # run t-tests for each timestamp
#    n=len(df_int.columns)
#    print("\nhand t calculations:")
#    int_p_values = df_int[:10].apply(t_tests.t_test_1sample, axis=1).astype("float").tolist()
#    other_p_values = df_other[:20].apply(t_tests.t_test_1sample, axis=1).astype("float").tolist()

    # factory function
    # print("\nfactory t calculations:")
    # int_p_fact = df_int.apply(t_tests.factory_1samp_t_test, axis=1).astype("float").tolist()
    # other_p_fact = df_other.apply(t_tests.factory_1samp_t_test, axis=1).astype("float").tolist()

#    print("\nhand calculated int p values (10-20):\n", int_p_values)
#    print("\nfactory calculated int p values (10-20):\n", int_p_fact)

    time_frame_int = list(df_int.index * 16.7)
    df_int["time"] = time_frame_int
    time_frame_other = list(df_other.index * 16.7)
    df_other["time"] = time_frame_other
#
    # df_p_int = pd.DataFrame({"p_value":int_p_fact, "time":time_frame_int})
    # df_p_other = pd.DataFrame({"p_value":other_p_fact, "time":time_frame_other})
##
    melted_int = pd.melt(df_int, id_vars=["time"], var_name="subject", value_name="target_look")
    melted_other = pd.melt(df_other, id_vars=["time"], var_name="subject", value_name="target_look")

    # load to plots
    _plot_time_course(melted_int, time_frame_int, label="interesting", nr=nr_int_trials) # df_p=df_p_int,
    _plot_time_course(melted_other, time_frame_other, label="other", nr=nr_bor_trials) # df_p=df_p_other,

    # df_int = df_int.assign(p_value = int_p_fact)
    # df_other = df_other.assign(p_value = other_p_fact)

    # load to excel
    _write_to_excel(df_int, writer2, "interesting_label")
    _write_to_excel(df_other, writer2, "other_label")
    writer2.save()



def _write_to_excel(df, writer, sheet):

    df.to_excel(writer, sheet_name=sheet, index=False)

    print("Excel file saved for '{0}'".format(sheet))


def _average(lst):
    return reduce(lambda x,y : x+y, lst) / len(lst)


def _contains(gazepoint, AOI):
    """Checks if a pair of coordinates is within an AOI. """

    if gazepoint == "invalid":
        return False

    gpx = gazepoint[0]
    gpy = gazepoint[1]
    aoix = AOI[0][0]
    aoiy = AOI[0][1]
    width = AOI[1]
    height = AOI[2]

    if ((aoix - width/2) <= gpx <= (aoix + width/2) and (aoiy - height/2) <= gpy <= (aoiy + height/2)):
        return True
    else:
        return False


def _calculate_onscreen_gaze(dataframe, start_times, end_times):
    """Calculates look on screen for the given list of periods."""

    onscreen_looks = []

    for n in range(len(start_times)):
        df = dataframe[(dataframe["TimeStamp"] >= start_times[n]) & (dataframe["TimeStamp"]< end_times[n])]
        valid_times = df["gazepoints"].apply(lambda x : x != "invalid").sum()
        onscreen_looks.append(valid_times / df["gazepoints"].size)

    return onscreen_looks


def _gazepoint_to_aoi(gazepoint, aoi_int, aoi_boring):
    """Checks if the gazepoint is in an aoi and returns the aoi label"""
    if gazepoint == "invalid":
        return "OUT"

    if _contains(gazepoint, aoi_int):
        return "INT"
    elif _contains(gazepoint, aoi_boring):
        return "BOR"
#    elif _contains(gazepoint, AOI_ag):
#        return "ATT"
    else:
        return gazepoint


def _calculate_target_look(tag, aoi_int, aoi_boring, baseline=0):
    """Returns target  (1 or 0) minus the baseline (if given) for each gazepoint.
        Target: interesting object
        but could be: target = label target - then baseline should be from the same
        also could count 'familiar' looks as 0?
    """

    if tag.lower() == "int":
        return 1 - baseline
    elif tag.lower() == "bor":
        return 0 - baseline
    else:
        return np.nan


def _plot_time_course(df, time_frame, df_p=None, trial_nr=None, label=None, nr=0):
    """Plots time course of (melted) dataframe with given time frame. Plot per trial number or label.
        df_p : dataframe of p values
        trial_nr: the number of the trial (1 or 2)
        label: the label
        nr: number of subjects
    """

    # marker_label1_start = 2110
    # marker_label1 = 2643
    # marker_label2_start = 4300
    # marker_label2 = 4875

    palette = sns.color_palette("husl", 3)

    my_dpi=96
    plt.figure(figsize=(1920/my_dpi, 1080/my_dpi), dpi=my_dpi)
    if label==None:
        plt.title(f"Test round {trial_nr} - Baseline corrected target look mean (with SE)\n of N = {nr} subjects")
    else:
        plt.title(f"Baseline corrected target look mean (with SE)\n for the '{label}' label; N = {nr}")
    # ci (confidence interval) is set to 68 which will correspond to the standard error if the data is normally distributed, or else to the 68% of confidence interval
    sns.lineplot(x="time", y="target_look", data=df, ci=68, palette=palette, label="proportional target look")

    if df_p:
        sns.lineplot(x="time", y="p_value", data=df_p, palette=palette, label="p_value")
#    sns.lineplot(x="time", y="p_values", data=df_p, ci=None, label="p-values")

    plt.axhline(0, ls='--', c="r", label="chance")
    # plt.axvline(marker_label1_start, c="purple", label="label 1 starts")
    # plt.axvline(marker_label1, c="purple", label="label 1 ends")
    # plt.axvline(marker_label2_start, c="green", label="label 2 starts")
    # plt.axvline(marker_label2, c="green", label="label 2 ends")
#    plt.axhline(0.05, ls='--', c="black", label="significance level: 0.05")
    plt.xticks(np.arange(min(time_frame), max(time_frame)+100, 300))
    plt.yticks(np.arange(-1.1, 1.1, 0.1))
    plt.xlabel('Time in ms')
    plt.ylabel('Proportion')
    plt.legend()
    if label==None:
        plt.savefig(os.path.join(plots_dirname, f"curiosity_prop_tls_trial{trial_nr}_bl_corr_{date}.png"), dpi=my_dpi)
        print(f"Plot saved for trial {trial_nr}")
    else:
        plt.savefig(os.path.join(plots_dirname, f"curiosity_prop_tls_'{label}'_label_bl_corr_{date}.png"), dpi=my_dpi)
        print(f"Plot saved for {label} label.")

#    plt.show()


def test_interesting_positions(positions):

    all_positions = ["bottom-left", "bottom-right", "top-left", "top-right"]
    assert ((positions[0] in all_positions) and (positions[1] in all_positions)), "invalid interesting position"


if __name__ == "__main__":
    main()


