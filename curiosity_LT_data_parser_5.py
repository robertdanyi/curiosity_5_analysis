# -*- coding: utf-8 -*-
"""
Parsing eyetracker data of Curiosity Exp 4 test objects 08-05-

TODO: define a velocity threshold to categorise between saccades and fixations.
Then from the distribution of fixations, decide the fixation duration threshold.
Total looking times and first looks should all be fixations.

Data processing:
    - read
    - transformations:
        - gazepoints columns from GazePointX and GazePointY ("invalid", if no data)
        - restructuring data: remove event rows from df. set new, successive indices
        - interpolation of not justified gaps (gaps < 101 ms)
    (- calculate velocity for each sample; add velocity column
    - classify fixations)
    - calculate onscreen looks
    - check if ag fixation
    - calculate baseline fixations
    - calculate first look (fixation)
    - calculate test onint fixations



"""
import datetime
import os
import logging
import collections
import pandas as pd
import constants_times_5 as c
import reading_and_transformations as rt
import calculations as calc

pd.options.mode.chained_assignment = None

logtime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
log = os.path.join(c.DIR, "runlogs", "curiosity_LT_parser_{0}.log".format(logtime))
logging.basicConfig(filename=log, level=logging.DEBUG)

date = str(datetime.date.today())
dir_name = os.path.join(c.DIR, "tables", date)
logfiles = os.path.join(c.DIR, "data_to_read")
excelfile = os.path.join(dir_name, "curiosity_looking_data_{0}.xlsx".format(date))
# excelfile = os.path.join(c.DIR, "tables", "test_prints", "curiosity_looking_data_TEST_{0}.xlsx".format(date))
writer = pd.ExcelWriter(excelfile)

# AOI namedtuple
AOI = collections.namedtuple("AOI", "inter, bor, fam1, fam2")



def main():

    for log in os.listdir(logfiles):
        print("\nReading file {0}.".format(log))

        logfilepath = os.path.join(logfiles, log)

        df = rt.read_tsv_file(logfilepath)
        subj_nr = log.split("_")[0]

        if df is None:
            print("!!!WARNING! The file '{}' is compromised. Please check.".format(log))
            break

        df_events, df = rt.detach_events(df)
        events = df_events["Event"].tolist()

        # if exp was not completed, don't bother
        if not check_if_completed(events, subj_nr): break

        df = rt.interpolate_missing_samples(df)

        parse_introduction_data(df, df_events, subj_nr)
        parse_familiarisation_data(df, df_events, subj_nr)
        parse_test_data(df, df_events, subj_nr)

    try:
        os.mkdir(dir_name)
    except FileExistsError:
        pass

    writer.save()
    print("Excel file saved.")


def parse_introduction_data(df, df_events, subj_nr):

    fam = c.Fam_data(df_events)
    fam_onscreen = calc.calculate_onscreen_gaze(df, fam.start_times, fam.end_times)
    fam_label_onscreen = calc.calculate_onscreen_gaze(df, fam.label_start_times, fam.label_end_times)

    output_fam = pd.DataFrame({"Fam_objs_LT-screen": fam_onscreen,"Fam_labeling_LT-screen":fam_label_onscreen})
    output_fam.to_excel(writer, sheet_name=subj_nr, index=False)


def parse_familiarisation_data(df, df_events, subj_nr):

    teaching = c.Teaching_data(df_events)
    start_times, end_times = teaching.start_times, teaching.end_times
    teaching_demo_onscreen = calc.calculate_onscreen_gaze(df, start_times, end_times)
    teaching_label_onscreen = calc.calculate_onscreen_gaze(df, teaching.label_start_times, teaching.label_end_times)

    events = df_events["Event"].tolist() # event e.g. "Familiarisation_anim1_left2"
    teaching_interesting_sides = [e.split("_")[-1][:-1] for e in events if (e.startswith("Familiarisation_anim"))]
    logging.info("Subject: {0} \nFamiliarisation interesting sides: {1}".format(subj_nr, teaching_interesting_sides))
    # print("\t--> Familiarisation interesting sides:", teaching_interesting_sides)

    teaching_onint = []
    for n in range(len(end_times)):

        int_side = teaching_interesting_sides[n]
        aoi = AOI(inter=c.AOI_left if int_side == "left" else c.AOI_right,
                  bor=c.AOI_right if int_side == "left" else c.AOI_left,
                  fam1=None, fam2=None)
        teaching_df = rt.assign_aoi_tags(df, start_times[n], end_times[n], aoi)
        teach_gaze = calc.collect_gaze(teaching_df)
        teaching_onint_gaze = teach_gaze.calculate_onobject_gaze()[0]
        teaching_onint.append(teaching_onint_gaze)

    output_new = pd.DataFrame({"New_objs_LT-screen": teaching_demo_onscreen, "New_objs_LT-interesting": teaching_onint,
                                "New_labeling_LT-screen": teaching_label_onscreen})
    output_new.to_excel(writer, sheet_name=subj_nr, index=False, startrow=7)


def parse_baseline_data(df, baselines, aoi, start_time=None, end_time=None, subj_nr=None):
    """
    Baselines are calculated in proportion to the sum gaze to the interesting, boring
    and familar objects.
    """

    bl_df = rt.assign_aoi_tags(df, start_time, end_time, aoi)
    bl_gaze = calc.collect_gaze(bl_df)
    bl_onint, bl_onboring, _ = bl_gaze.calculate_onobject_gaze()
    baselines["int"].append(bl_onint)
    baselines["bor"].append(bl_onboring)

    return bl_onint, bl_onboring


def check_att_getter_look(df, test, n, aoi):

    start = test.ag_start_times[n]
    end = test.start_times[n]

    ag_df = rt.assign_aoi_tags(df, start, end, aoi, aoi_ag=c.AOI_ag)
    ag_gaze = calc.collect_gaze(ag_df)
    looked_at_ag = "Yes" if "ATT" in ag_gaze.get_taglist() else "No"
    last_gazepoint = ag_df["aoi"].tolist()[-1]

    return looked_at_ag, last_gazepoint


def parse_test_data(df, df_events, subj_nr):

    gaze_cat = {"INT":1, "BOR":2, "FAM":3}

    test = c.Test_data(df_events)
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

    test_results = c.Test_results(subj_nr)

    baselines = {"int":[], "bor":[]}

    for n in range(len(end_times)):

        # AOIs in round n
        int_side = test_interesting_sides[n]
        aoi = AOI(inter=c.AOI_dict[int_side][0],
              bor=c.AOI_dict[int_side][1],
              fam1=c.AOI_dict[int_side][2],
              fam2=c.AOI_dict[int_side][3])

        # parse baseline in round
        bl_onint, bl_onboring = parse_baseline_data(df, baselines, aoi,
                                                    start_time=test.bl_start_times[n], end_time=test.ag_start_times[n],
                                                    subj_nr=subj_nr)

        # check att getter fixation
        looked_at_ag, preceding_look = check_att_getter_look(df, test, n, aoi)
        test_results.ag_looks.append(looked_at_ag)
        test_results.preceding_looks.append(preceding_look if isinstance(preceding_look, str) else "no_aoi")

        # TEST PHASE
        test_start, test_end = start_times[n], end_times[n]
        test_df = rt.assign_aoi_tags(df, test_start, test_end, aoi)
        # print test
        print_dataframes(test_df, subj_nr, "test_df_aois_{0}_round{1}".format(subj_nr, n+1))

        # first gaze
        test_gaze = calc.collect_gaze(test_df)
        # print("--> test_gaze:", test_gaze._dict)
        tag1, time1, duration1 = test_gaze.get_gaze_data(gaze_nr=1)
        latency1 = (time1 - test_start) if time1 else None
        first_gaze_tag = gaze_cat[tag1] if tag1 else None
        first_gaze_duration = duration1 * 16.7 if duration1 else None

        test_results.first_gazes.append(first_gaze_tag)
        test_results.first_gaze_latencies.append(latency1)
        test_results.first_gaze_durations.append(first_gaze_duration)

        # second gaze
        tag2, time2, duration2 = test_gaze.get_gaze_data(gaze_nr=2)
        latency2 = (time2 - test_start) if time2 else None
        second_gaze_tag = gaze_cat[tag2] if tag2 else None
        second_gaze_duration = duration2 * 16.7 if duration2 else None

        test_results.second_gazes.append(second_gaze_tag)
        test_results.second_gaze_latencies.append(latency2)
        test_results.second_gaze_durations.append(second_gaze_duration)
        # print("--> test_results.second_gaze_durations", test_results.second_gaze_durations)

        # gaze on interesting and on boring object during test # not corrected
        test_onint_gaze, test_onboring_gaze, test_onfam_gaze = test_gaze.calculate_onobject_gaze()
        test_results.all_test_onint.append(test_onint_gaze)
        test_results.all_test_onboring.append(test_onboring_gaze)
        test_results.all_test_onfam.append(test_onfam_gaze)

        # gaze on interesting and on boring object # bl-corrected
        test_onint_gaze_bl = test_onint_gaze - bl_onint
        test_results.all_test_onint_bl_corr.append(test_onint_gaze_bl)
        test_onboring_gaze_bl = test_onboring_gaze - bl_onboring
        test_results.all_test_onboring_bl_corr.append(test_onboring_gaze_bl)

        # gaze on familiar objects
        test_onfam_gaze

        # logging
        label = start_events[n].split("_")[-2]
        logging.info("Label for test round {0}: {1}".format(str(n+1), label))
#        logging.debug("\nfirst_gaze_tag: {0} \nfirst_gaze_time: {1} \nfirst_gaze_duration: {2}".format(first_gaze_tag, latency1, first_gaze_duration))
#        logging.debug("\nsecond_gaze_tag: {0} \nsecond_gaze_time: {1} \nsecond_gaze_duration: {2}".format(second_gaze_tag, latency2, second_gaze_duration))

    write_results_to_file(test_results, bl_onscreen, test_onscreen, baselines)


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


def write_results_to_file(test_results, bl_onscreen, test_onscreen, baselines):

    output_df = pd.DataFrame({"Test label": ["interesting", "other"],
                              "Baseline_LT-screen":bl_onscreen,
                              "Test_LT-screen": test_onscreen,
                              "Baseline_LT-interesting": baselines["int"],
                              "Baseline_LT-other": baselines["bor"],
                              "Gaze_on_AG": test_results.ag_looks,
                              "Look_before_end_of_label":test_results.preceding_looks,
                              "Test_LT_interesting":test_results.all_test_onint,
                              "Test_LT_other":test_results.all_test_onboring,
                              "Test_LT_familiars":test_results.all_test_onfam,
                              "Test_LT-interesting_BL-corr.": test_results.all_test_onint_bl_corr,
                              "Test_LT_other_BL-corr.": test_results.all_test_onboring_bl_corr,
                              "1st_gaze_after_label": test_results.first_gazes,
                              "1st_gaze_latency": test_results.first_gaze_latencies,
                              "1st_gaze_duration":test_results.first_gaze_durations,
                              "2nd_gaze_after_label": test_results.second_gazes,
                              "2nd_gaze_latency": test_results.second_gaze_latencies,
                              "2nd_gaze_duration":test_results.second_gaze_durations
                              })

    output_df.to_excel(writer, sheet_name=test_results.subj_nr, index=False, startrow=15)


## for testing
def print_dataframes(df, subj_nr, filename):

    if filename[-4:] != "xlsx":
        filename += ".xlsx"
    excel = os.path.join(c.DIR, "tables", "test_prints", filename)
    writer = pd.ExcelWriter(excel)
    df.to_excel(writer, sheet_name=subj_nr)
    writer.save()


if __name__ == "__main__":
    main()


###########################


# TODO
def calculate_fixations(df, start_time, end_time, threshold=151, freq=60):
    """
    Calculate fixations on target object within the specified period.
    Default threshold is 151 ms -> 9 samples in 60 fps (16.7 ms samples)
    - adds fixation column to database with tag "fix" if timepoint is within a (on-target) fixation period.
    """
    return df




