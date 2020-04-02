# -*- coding: utf-8 -*-
"""
Parsing eyetracker data of Curiosity Exp V5

TODO: define a velocity threshold to categorise between saccades and fixations.
Then from the distribution of fixations, decide the fixation duration threshold.
Total looking times and first looks should all be fixations.

Data processing structure:
    - read (reading_and_transformations.read_tsv_file)
        - read tsv file (with format checking), load to dataframe
        - create "gazepoints" column from "GazePointX" and "GazePointY" ("invalid", if no data)
    - transformations:
        - restructuring data: remove event rows from df. (rt.detach_events)
        - set new, successive indices (rt.interpolate_missing_samples)
        - interpolation of not justified gaps (gaps < 101 ms) (rt.interpolate_missing_samples)

    ((- calculate velocity for each sample; add velocity column
    - classify fixations)) - to be implemented

    - parse_introduction_data
        - calculate onscreen fixation sum for presentation and labeling _calculate_onscreen_look)

    - parse_familiarisation_data
        - calculate onscreen fixation sum for presentation and labeling (_calculate_onscreen_look)
        - calculate fixation sum for each interesting object (calculations.collect_gaze,
          gaze.calculate_onobject_gaze)

    - parse_test_data
        - calculate onscreen fixation sum for baseline and test periods (_calculate_onscreen_look)

        For each test round:
            - calculate baseline fixation sums for each object (calculations.collect_gaze,
              gaze.calculate_onobject_gaze)
            - check ag fixation (calculations.collect_gaze)
            - check trial validity based on above results
            - collect test looking time data (baselines, onobject gazes, bl-corrected onobject gazes)
            - calculate gaze structure
            - collect gaze data from gaze structure (gaze.sort_gaze)
            - collect time course data (baselines and AOI tags from gaze period)
   
###############################################################################         
Change logs:
------------
2020.02.24
- only apple and banana (from 02.24)
- slightly changed loglines (see constants)

2020.02.26
3 rounds of familiarisation instead of 4
1s blank before each test trial (instead of .5)
"""

import datetime
import os
import logging
import collections
import pandas as pd
import pickle
import swifter
import constants as c
import reading_and_transformations as rt
import gaze_calculations as calc
import looking_time_aggregations as aggr
import time_course_plotting as time_course

pd.options.mode.chained_assignment = None


####################
test = False
save_to_file = True
do_aggregation = False
analyse_tc = False
save_tc_pickle = False
####################

logtime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
log = os.path.join(c.DIR, "runlogs", "curiosity_LT_parser_{0}.log".format(logtime))
logging.basicConfig(filename=log, level=logging.DEBUG)

date = str(datetime.date.today())
dir_name = os.path.join(c.DIR, "tables", date)
test_dir_name = os.path.join(c.DIR, "tables", "test_prints", date)
tc_dfs_dir_name = os.path.join(c.DIR, "time_course", "subj_dataframes")
pickle_jar = os.path.join(c.DIR, "time_course", "pickle")

if test:
    logfilespath = os.path.join(c.DIR, "data_to_read_TEST")
    excelfile = os.path.join(test_dir_name, "curiosity_looking_data_TEST_{0}.xlsx".format(date))
else:
    logfilespath = os.path.join(c.DIR, "data_to_read")
    excelfile = os.path.join(dir_name, "curiosity_looking_data_{0}.xlsx".format(date))
    
writer = pd.ExcelWriter(excelfile)


# AOI namedtuple
AOI = collections.namedtuple("AOI", "inter, bor, fam1, fam2")



def main():
    
    _create_paths([dir_name, test_dir_name, pickle_jar])
    
    ord_dict = {}
    time_course_dict = {}

    logfiles = [f for f in sorted(os.listdir(logfilespath)) if os.path.isfile(os.path.join(logfilespath, f))]
    
    for log in logfiles:
        print(f"\nReading file {log}")
        
        # check date of logfile
        datestring = log.split("_")[3]
        logdate = datetime.datetime.strptime(datestring, "%Y-%m-%d")
        feb24 = datetime.datetime(2020, 2, 24)
        oldlog = logdate < feb24

        logfilepath = os.path.join(logfilespath, log)

        df = rt.read_tsv_file(logfilepath)
        subj_nr = log.split("_")[0]

        if df is None:
            print(f"!!!WARNING! The file '{log}' is compromised. Please check.")
            break

        df_events, df = rt.detach_events(df)
        events = df_events["Event"].tolist()

        # if exp was not completed, don't bother
        if not check_if_completed(events, subj_nr): 
            break

        df = rt.interpolate_missing_samples(df)
        
        # objects holding logged times and events
        fam = c.Fam_data(df_events)
        teaching = c.Teaching_data(df_events, oldlog)
        test = c.Test_controll_data(df_events, oldlog)

        valid1 = parse_introduction_data(df, fam, subj_nr)
        valid2 = parse_familiarisation_data(df, teaching, subj_nr)
        test_results_df, gaze_results_df, time_course_d = parse_test_data(df, test, subj_nr)
        
        if valid1 and valid2:
            
            # add time_course dict to main dict to send
            time_course_dict[subj_nr] = time_course_d
            # reset index of gaze_df from labels to default
            gaze_results_df.reset_index(drop=True, inplace=True)
            # flatten multi-level columns and create string column name from tuple
            gaze_results_df.columns = [" ".join(col) for col in gaze_results_df.columns.to_flat_index()]
            # add dfs to main dict
            ord_dict[subj_nr] = [test_results_df, gaze_results_df]
                    
            
    if save_to_file:
        writer.save()
        print("Excel file with separate subject sheets is saved.")
    
    if do_aggregation:
        aggr.aggregate_data(ord_dict)
        
    if analyse_tc:
        time_course.analyse_time_course(time_course_dict)
    
    if save_tc_pickle:
        # save time_course_dict in a pickle
        with open(os.path.join(pickle_jar, "tc_dict" + '.pkl'), 'wb') as f:
            pickle.dump(time_course_dict, f, pickle.HIGHEST_PROTOCOL)
            print("pickle file saved")
    
    

def parse_introduction_data(df, fam, subj_nr):

    fam_onscreen = _calculate_onscreen_look(df, fam.start_times, fam.end_times)
    fam_label_onscreen = _calculate_onscreen_look(df, fam.label_start_times, fam.label_end_times)

    output_fam = pd.DataFrame({"Fam_objs_LT-screen": fam_onscreen,"Fam_labeling_LT-screen":fam_label_onscreen})
    
    if save_to_file:
        write_results_to_file(output_fam, subj_nr, index=False, startrow=0)
    
    if (
        (sum(fam_onscreen)/len(fam_onscreen) < 0.6) or 
        (sum(fam_label_onscreen)/len(fam_label_onscreen) < 0.6)
        ):
        print(f"{subj_nr} not enough intro (or intro label) onscreen")
        return False
    
    return True


def parse_familiarisation_data(df, teaching, subj_nr):

    start_times, end_times = teaching.start_times, teaching.end_times
    
    teaching_demo_onscreen = _calculate_onscreen_look(df, start_times, end_times)
    teaching_label_onscreen = _calculate_onscreen_look(df, teaching.label_start_times, teaching.label_end_times)

    teaching_interesting_sides = teaching.interesting_sides
    logging.info("Subject: {0} \nFamiliarisation interesting sides: {1}".format(subj_nr, teaching_interesting_sides))

    teaching_onint = [] # needed to see if int is really interesting
    for n in range(len(end_times)):

        int_side = teaching_interesting_sides[n]
        aoi = AOI(inter=c.AOI_left if int_side == "left" else c.AOI_right,
                  bor=c.AOI_right if int_side == "left" else c.AOI_left,
                  fam1=None, fam2=None)

        start, end = start_times[n], end_times[n]
        teaching_df = df[(df["TimeStamp"] > start) & (df["TimeStamp"] < end)]
        teaching_df = rt.assign_aoi_tags(teaching_df, aoi)
        teach_gaze = calc.collect_gaze(teaching_df)
        teaching_onint_gaze = teach_gaze.calculate_onobject_gaze()[0]
        teaching_onint.append(teaching_onint_gaze)

    output_new = pd.DataFrame({"New_objs_LT-screen": teaching_demo_onscreen, "New_objs_LT-interesting": teaching_onint,
                                "New_labeling_LT-screen": teaching_label_onscreen})
    
    if save_to_file:
        write_results_to_file(output_new, subj_nr, index=False, startrow=7)
    
    if (
        (sum(teaching_demo_onscreen)/len(teaching_demo_onscreen) < 0.6) or
        (sum(teaching_label_onscreen)/len(teaching_label_onscreen) < 0.6)
        ):
        print(f"{subj_nr} not enough teaching (or teaching label) onscreen")
        return False
    
    return True


def parse_baseline_data(df, aoi, start_time=None, end_time=None):
    """
    Baselines are calculated in proportion to the sum gaze to the interesting, boring
    and familar objects.
    """

    bl_df = df[(df["TimeStamp"] > start_time) & (df["TimeStamp"] < end_time)]
    bl_df = rt.assign_aoi_tags(bl_df, aoi)
    bl_gaze = calc.collect_gaze(bl_df)
    bl_onint, bl_onboring, bl_onfam = bl_gaze.calculate_onobject_gaze()

    return bl_onint, bl_onboring, bl_onfam


def check_att_getter_gaze(df, test, n, aoi):

    start = test.ag_start_times[n]
    end = test.start_times[n]

    ag_df = df[(df["TimeStamp"] > start) & (df["TimeStamp"] < end)]
    ag_df = rt.assign_aoi_tags(ag_df, aoi, aoi_ag=c.AOI_ag)
    ag_gaze = calc.collect_gaze(ag_df)
    gazed_at_ag = True if "ATT" in ag_gaze.get_taglist() else False

    return gazed_at_ag


def parse_test_data(df, test, subj_nr):
    """
    returns:
        test_results_df from test_dict:
            
        gaze_results_df from gaze_dict:
            dict to collect gaze structure data
                 keys: "familiar", "novel"
                 values: sorted gaze structure dictionary
                     
        time_course_d:
            dict to collect data for time course analysis
                keys: 
                     level 0: 0,1...
                     level 1: BL_INT, BL_BOR, aoi
    """
    test_dict = {}
    
    gaze_dict = {}
    
    time_course_d = {}

    start_times, end_times = test.start_times, test.end_times
    test_interesting_sides = test.interesting_sides

    logging.info("Subject: {0} \nTest interesting sides: {1}".format(subj_nr, test_interesting_sides))

    # ALERT if tests not completed
    if not check_tests_validity(len(end_times)): return

    # onscreen results
    bl_onscreen = _calculate_onscreen_look(df, test.bl_start_times, test.ag_start_times)
    test_onscreen = _calculate_onscreen_look(df, start_times, end_times)
    
    
    for n in range(len(end_times)): # n: trial nr
        
        # trial validity
        valid = True
        
        # AOIs in round n
        int_side = test_interesting_sides[n]
        aoi = AOI(inter=c.AOI_dict[int_side][0],
              bor=c.AOI_dict[int_side][1],
              fam1=c.AOI_dict[int_side][2],
              fam2=c.AOI_dict[int_side][3])

        # check att getter fixation
        gazed_at_ag = check_att_getter_gaze(df, test, n, aoi)
        
        # check validity
        if ( 
                (not gazed_at_ag) or
                (bl_onscreen[n] < 0.6) or 
                (test_onscreen[n] < 0.6) 
            ):
            valid = False
        
        # parse baseline in round
        bl_onint, bl_onboring, bl_onfam, = parse_baseline_data(df, aoi,
                                                    start_time=test.bl_start_times[n],
                                                    end_time=test.ag_start_times[n])
        
        # LOOKING TIME
        test_start, test_end = start_times[n]-339, end_times[n]
        test_df = df[(df["TimeStamp"] >= test_start) & (df["TimeStamp"] <= test_end)]
        test_df = rt.assign_aoi_tags(test_df, aoi)
        test_all_gaze_coll = calc.collect_gaze(test_df)

        test_onint_gaze, test_onboring_gaze, test_onfam_gaze = test_all_gaze_coll.calculate_onobject_gaze()
        
        valid_trial = valid
        test_label = "Familiar" if n%2==0 else "Novel"
        
        # collect test data  - Is the trial valid if there was no gaze response?
        td = dict(Test_label = test_label,
                  Baseline_LT_screen = bl_onscreen[n],
                  Gazed_at_AG = gazed_at_ag,
                  Test_LT_screen = test_onscreen[n],
                  Baseline_INT = bl_onint,
                  Baseline_BOR = bl_onboring,
                  Baseline_FAMS = bl_onfam,
                  TEST_INT = test_onint_gaze,
                  TEST_BOR = test_onboring_gaze,
                  TEST_FAMS = test_onfam_gaze,
                  TEST_INT_bl_corr = test_onint_gaze - bl_onint,
                  TEST_BOR_bl_corr = test_onboring_gaze - bl_onboring,
                  TEST_FAMS_bl_corr = test_onfam_gaze - bl_onfam,
                  Valid_trial = valid_trial
                  )
        test_dict[n] = td
        
        # FIRST GAZE for gp: gaze period
        gp_start, gp_end = start_times[n]-339, start_times[n]+2000
        gp_df = df[(df["TimeStamp"] >= gp_start) & (df["TimeStamp"] <= gp_end)]
        gp_df = rt.assign_aoi_tags(gp_df, aoi)
        
        gaze_structure = calc.collect_gaze(gp_df)
        gaze_d, responded = gaze_structure.sort_gaze(nr_of_gazes=3, start_time=gp_start)
        label = ["Familiar","Novel"][n%2]
        gaze_dict[label]=gaze_d
        
        if valid: # only add if valid trial
            
            tcd = dict(responded=responded,
                       BL_INT = bl_onint, 
                       BL_BOR = bl_onboring,
                       BL_FAM = bl_onfam,
                       AOI = gp_df["aoi"].tolist() #reset_index(drop=True)
#                       AOI = test_df["aoi"].reset_index(drop=True) 
                     )
            
            time_course_d[n] = tcd

        # logging
#        label = start_events[n].split("_")[-2]
#        logging.info("Label for test round {0}: {1}".format(str(n+1), label))
     
        test_results_df = pd.DataFrame(test_dict).T
        gaze_results_df = pd.DataFrame(gaze_dict).T
    
    if save_to_file:
        write_results_to_file(test_results_df, subj_nr, index=False, startrow=15)
        write_results_to_file(gaze_results_df, subj_nr, index=True, startrow=21)
    
    return test_results_df, gaze_results_df, time_course_d


def _calculate_onscreen_look(dataframe, start_times, end_times):
    """ returns a list of proportional looking times on screen for each trial"""

    onscreen_looks = []

    for n in range(len(start_times)):
        df = dataframe[(dataframe["TimeStamp"] >= start_times[n]) & (dataframe["TimeStamp"]< end_times[n])]
        valid_times = df["gazepoints"].swifter.progress_bar(False).apply(lambda x : x != "invalid").sum()
        onscreen_looks.append(valid_times / df["gazepoints"].size)

    return onscreen_looks


### Checkups ###
def check_if_completed(events, subj_nr):
    if c.EXP_COMPLETED not in events:
        print("!! Experiment was NOT COMPLETED.\n!! Subject {0} has no valid data".format(subj_nr))
        logging.warning("!! Experiment was NOT COMPLETED.\n!! Subject {0} has no valid data".format(subj_nr))
        return False
    else:
        return True


def check_tests_validity(n):
    if n < 2:
        print("\n!! UNFINISHED TEST!")
        logging.warning("UNFINISHED TEST")
        return False
    else:
        return True


### Print, round ###
def write_results_to_file(df, subj_nr, index=False, startrow=15):
    """
    Writes input df to file excel file.
    """
    
    def round_numbers(x):

        if isinstance(x, (float, complex)):
            return round(float(x),3)
        else:
            return x
    
    # rounding
    df = df.applymap(round_numbers)
    df.to_excel(writer, sheet_name=subj_nr, index=index, startrow=startrow)


    
## for testing
def print_dataframes(df, subj_nr, filename):

    if filename[-4:] != "xlsx":
        filename += ".xlsx"
    excel = os.path.join(c.DIR, "tables", "test_prints", filename)
    writer = pd.ExcelWriter(excel)
    df.to_excel(writer, sheet_name=subj_nr)
    writer.save()

    
def _create_paths(paths):
    
    for path in paths:
        try: 
            os.makedirs(path)
        except FileExistsError: 
            pass


if __name__ == "__main__":
    main()


###########################


# TODO
def calculate_fixations(df, start_time, end_time, threshold=151, freq=60):
    """
    Calculate fixations on target object within the specified period.
    Default threshold is 151 ms -> 9 samples in 60 fps (ST ms samples)
    - adds fixation column to database with tag "fix" if timepoint is within a (on-target) fixation period.
    """
    return df

