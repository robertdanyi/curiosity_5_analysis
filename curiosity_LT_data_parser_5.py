# -*- coding: utf-8 -*-
"""
Parsing eyetracker data of Curiosity Exp 4 test objects 08-05-

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
        - calculate onscreen fixation sum for presentation and labeling (calc.calculate_onscreen_gaze)

    - parse_familiarisation_data
        - calculate onscreen fixation sum for presentation and labeling (calc.calculate_onscreen_gaze)
        - calculate fixation sum for each interesting object (calculations.collect_gaze,
          gaze.calculate_onobject_gaze)

    - parse_test_data
        - calculate onscreen fixation sum for baseline and test periods (calc.calculate_onscreen_gaze)

        For each test round:
            - calculate baseline fixation sums for each object (calculations.collect_gaze,
              gaze.calculate_onobject_gaze)
            - check ag fixation (calculations.collect_gaze)
            - calculate first gaze
            - calculate test fixation sums for each object (calculations.collect_gaze,
              gaze.calculate_onobject_gaze)

"""
import datetime
import os
import logging
import collections
import pandas as pd
import constants_times_5 as c
import reading_and_transformations as rt
import calculations as calc
import curiosity_LT_aggr_5 as aggr

pd.options.mode.chained_assignment = None

logtime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
log = os.path.join(c.DIR, "runlogs", "curiosity_LT_parser_{0}.log".format(logtime))
logging.basicConfig(filename=log, level=logging.DEBUG)

date = str(datetime.date.today())
dir_name = os.path.join(c.DIR, "tables", date)

test = False

if test:
    logfilespath = os.path.join(c.DIR, "data_to_read_TEST")
    excelfile = os.path.join(c.DIR, "tables", "test_prints", "curiosity_looking_data_TEST_{0}.xlsx".format(date))
else:
    logfilespath = os.path.join(c.DIR, "data_to_read")
    excelfile = os.path.join(dir_name, "curiosity_looking_data_{0}.xlsx".format(date))
    try: 
        os.mkdir(dir_name)
    except FileExistsError: 
        pass
    
writer = pd.ExcelWriter(excelfile)
    

# AOI namedtuple
AOI = collections.namedtuple("AOI", "inter, bor, fam1, fam2")


def main():
    
    ord_dict = {}

    logfiles = [f for f in sorted(os.listdir(logfilespath)) if os.path.isfile(os.path.join(logfilespath, f))]
    
    for log in logfiles:
        print(f"\nReading file '{log}'.")

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

        valid1 = parse_introduction_data(df, df_events, subj_nr)
        valid2 = parse_familiarisation_data(df, df_events, subj_nr)
        valid3, test_df, gaze_df = parse_test_data(df, df_events, subj_nr)
        
        if valid1 and valid2 and valid3:
            # reset index of gaze_df from labels to default
            gaze_df.reset_index(drop=True, inplace=True)
            # flatten multi-level columns
            gaze_df.columns = gaze_df.columns.to_flat_index()
            gaze_df.columns = [" ".join(col) for col in gaze_df.columns]
            # add dfs to main dict
            ord_dict[subj_nr] = [test_df, gaze_df]
            
    writer.save()
    print("Excel file with separate subject sheets is saved.")
    
    aggr.aggregate_data(ord_dict)
    

def parse_introduction_data(df, df_events, subj_nr):

    fam = c.Fam_data(df_events)
    fam_onscreen = calc.calculate_onscreen_gaze(df, fam.start_times, fam.end_times)
    fam_label_onscreen = calc.calculate_onscreen_gaze(df, fam.label_start_times, fam.label_end_times)

    output_fam = pd.DataFrame({"Fam_objs_LT-screen": fam_onscreen,"Fam_labeling_LT-screen":fam_label_onscreen})
    
    write_results_to_file(output_fam, subj_nr, index=False, startrow=0)
    output_fam.to_excel(writer, sheet_name=subj_nr, index=False)
    
    l = fam_onscreen 
    if sum(l)/len(l) < 0.7:
        print(f"{subj_nr} not enough intro onscreen")
        return False
    
    l_label =  fam_label_onscreen
    if sum(l_label)/len(l_label) < 0.7:
        print(f"{subj_nr} not enough intro label onscreen")
        return False
    
    return True


def parse_familiarisation_data(df, df_events, subj_nr):

    teaching = c.Teaching_data(df_events)
    start_times, end_times = teaching.start_times, teaching.end_times
    
    teaching_demo_onscreen = calc.calculate_onscreen_gaze(df, start_times, end_times)
    teaching_label_onscreen = calc.calculate_onscreen_gaze(df, teaching.label_start_times, teaching.label_end_times)

    events = df_events["Event"].tolist() # event e.g. "Familiarisation_anim1_left2"
    teaching_interesting_sides = [e.split("_")[-1][:-1] for e in events if (e.startswith("Familiarisation_anim"))]
    logging.info("Subject: {0} \nFamiliarisation interesting sides: {1}".format(subj_nr, teaching_interesting_sides))
#     print("\t--> Familiarisation interesting sides:", teaching_interesting_sides)

    teaching_onint = []
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
    
    write_results_to_file(output_new, subj_nr, index=False, startrow=7)
    output_new.to_excel(writer, sheet_name=subj_nr, index=False, startrow=7)
    
    l = teaching_demo_onscreen + teaching_label_onscreen
    if sum(l)/len(l) < 0.7:
        print(f"{subj_nr} not enough teaching onscreen")
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
    # print("\n---> BL df start time, BL end time:", start_time, end_time)
    # print("\n----> BL DF[10]:", bl_df.iloc[0:10])
    # print("\n--> bl_gaze:", bl_gaze._dict)
    bl_onint, bl_onboring, bl_onfam = bl_gaze.calculate_onobject_gaze()

    return bl_onint, bl_onboring, bl_onfam


def check_att_getter_gaze(df, test, n, aoi):

    start = test.ag_start_times[n]
    end = test.start_times[n]

    ag_df = df[(df["TimeStamp"] > start) & (df["TimeStamp"] < end)]
    ag_df = rt.assign_aoi_tags(ag_df, aoi, aoi_ag=c.AOI_ag)
    ag_gaze = calc.collect_gaze(ag_df)
#    gazed_at_ag = "Yes" if "ATT" in ag_gaze.get_taglist() else "No"
    gazed_at_ag = True if "ATT" in ag_gaze.get_taglist() else False

    return gazed_at_ag


def parse_test_data(df, df_events, subj_nr):
    
    valid = True

    gaze_cat = {"INT":1, "BOR":2, "FAM":3}
    
    test_dict = {"Test label": ["Familiar label", "Novel label"],
                 "Baseline_LT-screen":[],
                 "Gazed_at_AG?": [],
                 "Test_LT-screen": []
                }
    
    for col in c.quant_columns:
        test_dict[col] = []
    
#    print("test_dict keys:", test_dict.keys())

    gaze_dict = {}

    test = c.Test_controll_data(df_events)
    start_events = test.start_events
    start_times, end_times = test.start_times, test.end_times

    # test__int_label_bottom_right_tacok_STARTS
    test_interesting_sides = ["-".join(e.split("_")[-4:-2]) for e in start_events]
    logging.info("Subject: {0} \nTest interesting sides: {1}".format(subj_nr, test_interesting_sides))

    # ALERT if tests not completed
    if not check_tests_validity(len(end_times)): return

    # onscreen results
    bl_onscreen = calc.calculate_onscreen_gaze(df, test.bl_start_times, test.ag_start_times)
    test_onscreen = calc.calculate_onscreen_gaze(df, start_times, end_times)
    
    test_dict["Baseline_LT-screen"] = bl_onscreen
    test_dict["Test_LT-screen"] = test_onscreen
    
    for x in bl_onscreen + test_onscreen:
        if x < 0.6:
            valid = False
    
    for n in range(len(end_times)):

        # AOIs in round n
        int_side = test_interesting_sides[n]
        aoi = AOI(inter=c.AOI_dict[int_side][0],
              bor=c.AOI_dict[int_side][1],
              fam1=c.AOI_dict[int_side][2],
              fam2=c.AOI_dict[int_side][3])

        # parse baseline in round
        bl_onint, bl_onboring, bl_onfam, = parse_baseline_data(df, aoi,
                                                    start_time=test.bl_start_times[n],
                                                    end_time=test.ag_start_times[n])
        
        test_dict["Baseline_INT"].append(bl_onint)
        test_dict["Baseline_BOR"].append(bl_onboring)
        test_dict["Baseline_FAMS"].append(bl_onfam)

        # check att getter fixation
        gazed_at_ag = check_att_getter_gaze(df, test, n, aoi)
        test_dict["Gazed_at_AG?"].append(gazed_at_ag)
        
        if not gazed_at_ag:
            print(f"{subj_nr} didn't look at AG in trial {n+1}")
            valid = False

        # TEST PHASE
        """
        Label onset is at 2100ms.
        Before a 233ms latency, it cannot be considered a response.
        Mean 'no-overlap' response times for 24 month-olds is around 600 ms. (Swingley et al. 99)
        Since the "test start" is logged 572ms after label onset (at 2672), kids should start responding around the end of AG.
        Above 2000ms latency a gaze shift is not considered a response.
        Define 2 test periods:
            - test gaze period: from ag_start + 2333ms to ag_end+2000ms - to collect gazes - print out a gaze structure with up to 3 gazes
            - test look period: from ag_start + 2333ms to test_end - to collect on object gazes
        test_start = ag_start+2333 or test start time - 339
        
        UPDATE:We need initial gaze columns (object and latency) cor the gazes already ongoing at test_start
        """
        ## LOOKING TIME
        test_start, test_end = start_times[n]-339, end_times[n]
        test_df = df[(df["TimeStamp"] >= test_start) & (df["TimeStamp"] <= test_end)]
        test_df = rt.assign_aoi_tags(test_df, aoi)
        test_all_gaze_coll = calc.collect_gaze(test_df)

        test_onint_gaze, test_onboring_gaze, test_onfam_gaze = test_all_gaze_coll.calculate_onobject_gaze()
        test_dict["Test_INT"].append(test_onint_gaze)
        test_dict["Test_BOR"].append(test_onboring_gaze)
        test_dict["Test_FAMS"].append(test_onfam_gaze)

        # gaze on objects bl-corrected
        test_dict["Test_INT_bl-corr"].append(test_onint_gaze - bl_onint)
        test_dict["Test_BOR_bl-corr"].append(test_onboring_gaze - bl_onboring)
        test_dict["Test_FAMS_bl-corr"].append(test_onfam_gaze - bl_onfam)

        ## FIRST GAZE for gp: gaze period
        gp_start, gp_end = start_times[n]-339, start_times[n]+2000
        gp_df = df[(df["TimeStamp"] >= gp_start) & (df["TimeStamp"] <= gp_end)]
        gp_df = rt.assign_aoi_tags(gp_df, aoi)
        gaze_structure = calc.collect_gaze(gp_df)
        gaze_d = gaze_structure.sort_gaze(nr_of_gazes=3, start_time=gp_start)
        label = ["Familiar","Novel"][n]
        gaze_dict[label]=gaze_d
        
        # logging
        label = start_events[n].split("_")[-2]
        logging.info("Label for test round {0}: {1}".format(str(n+1), label))
#        logging.debug("\nfirst_gaze_tag: {0} \nfirst_gaze_time: {1} \nfirst_gaze_duration: {2}".format(first_gaze_tag, latency1, first_gaze_duration))
#        logging.debug("\nsecond_gaze_tag: {0} \nsecond_gaze_time: {1} \nsecond_gaze_duration: {2}".format(second_gaze_tag, latency2, second_gaze_duration))
    
    test_results_df = pd.DataFrame(test_dict)
    
    gaze_results_df = pd.DataFrame(gaze_dict).T
    
    write_results_to_file(test_results_df, subj_nr, index=False, startrow=15)
    write_results_to_file(gaze_results_df, subj_nr, index=True, startrow=21)
    
    return valid, test_results_df, gaze_results_df


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


def write_results_to_file(df, subj_nr, index=False, startrow=15):
    """
    Writes input df to file excel file.
    """
    # rounding
    df = df.applymap(round_numbers)
    df.to_excel(writer, sheet_name=subj_nr, index=index, startrow=startrow)


def round_numbers(x):

    if isinstance(x, (float, complex)):
        return round(float(x),3)
    else:
        return x


## for testing
def print_dataframes(df, subj_nr, filename):

    if filename[-4:] != "xlsx":
        filename += ".xlsx"
    excel = os.path.join(c.DIR, "tables", "test_prints", filename)
    writer = pd.ExcelWriter(excel)
    df.to_excel(writer, sheet_name=subj_nr)
    writer.save()


def _create_folder(folderpath):

    try:
        os.mkdir(folderpath)
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




