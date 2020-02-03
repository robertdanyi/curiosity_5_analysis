# -*- coding: utf-8 -*-
"""
constants and getters for curiosity 4-test-objects analysis

events:
    2x
    intro_with_face_start
    familiar_objects_shown
    Labeling_fam_object_STARTS
    labeling_fam_occluders_up
    Labeling_fam_object_ENDS

    4x
    # !! "face_start" comes after the "_anim_" log, so start times should be 180 frames = 3000 ms after "_anim_"
    Familiarisation_anim[1,2,3,4]_[left,right][1,2]
    intro_with_face_start
    occluders_going_down
    shuffle_starts
    Labeling_test_object_STARTS
    Labeling_test_object_ENDS

    2x
    lifting_occluders
    baseline_starts
    att_gett_starts_baseline_ends
    test__int_label_[bottom-right]_[tacok]_STARTS / test__other_label_[top-left]_[bitye]_STARTS
    test__int_label_ENDS / test__other_label_ENDS
    Experiment_ended
"""

import os


DIR = os.path.dirname(os.path.abspath(__file__))

# AOIs
# TODO: change to smaller aois
# NOTE: Tobii's output coordinates system: top-left: 0,0; center: 960,600; bottom-right: 1920,1200
AOI_left = [(480, 600), 640, 640] # x:160-800, y:280-920
AOI_right = [(1440, 600), 640, 640] # x:1120-1760, y:280-920

DS = (1920, 1200) # Display Size   (1280, 720) ---- Tobii t60xl: (1920 x 1200) screen ratio: 16/10...
X = DS[0]    # left or right part of screen: 960 - Tobii: 960
Y = DS[1]    # bottom or top part of screen: 540 - Tobii: 600

top_left = (X*0.25, Y*0.25) # 480, 300
bottom_left = (X*0.25, Y*0.75) # 480, 900
top_right = (X*0.75, Y*0.25) # 1440, 300
bottom_right = (X*0.75, Y*0.75) # 1440,900
width, height = 520, 520

# 4 test AOIs
AOI_top_left = [top_left, width, height]
AOI_bottom_left = [bottom_left, width, height]
AOI_top_right = [top_right, width, height]
AOI_bottom_right = [bottom_right, width, height] #

AOI_dict = {"top-left":[AOI_top_left,AOI_bottom_right,AOI_bottom_left,AOI_top_right],
            "bottom-left":[AOI_bottom_left,AOI_top_right,AOI_top_left,AOI_bottom_right],
            "top-right":[AOI_top_right,AOI_bottom_left,AOI_bottom_right,AOI_top_left],
            "bottom-right":[AOI_bottom_right,AOI_top_left,AOI_top_right,AOI_bottom_left]}

# to get aois for the familiar objects as well.
DIAG1 = (AOI_top_left,AOI_bottom_right)
DIAG2 = (AOI_bottom_left,AOI_top_right)
AOI_screen = [DIAG1,DIAG2]

AOI_ag = [(960,600), 320,320] # x:760-1160, y:420-780


# event strings
#EXP_STOPPED = "Experiment_was_stopped"
EXP_COMPLETED = "Experiment_ended"
FAM_DEMO = "familiar_objects_shown"
FAM_LBL_START = "Labeling_fam_object_STARTS"
FAM_LBL_END = "Labeling_fam_object_ENDS"
TEACH_LBL_START = "Labeling_test_object_STARTS"
TEACH_LBL_END = "Labeling_test_object_ENDS"
ATT_GETT_START = "att_gett_starts_baseline_ends"
TEST_EVENT_STARTSWITH = "test__"
TEST_START_EVENT_ENDSWITH = "STARTS"
TEST_END_EVENT_ENDSWITH = "ENDS"
BASELINE_EVENT = "baseline_starts"

fam_demo_dur = 6000
anim_dur = 12533

# columns to use for validation
teach_validation_columns = ["New_objs_LT-screen",
                 "New_labeling_LT-screen"]
test_validation_columns = ["Baseline_LT-screen",
                "Test_LT-screen",
                "Gaze_on_AG"]

columns = ["Test label",
          "Baseline_LT-screen",
          "Test_LT-screen",
          "Baseline_LT-interesting",
          "Baseline_LT-other",
          "Gaze_on_AG",
          "Look_before_end_of_label",
          "Test_LT_interesting",
          "Test_LT_other",
          "Test_LT_familiars",
          "Test_LT-interesting_BL-corr.",
          "Test_LT_other_BL-corr.",
          "1st_gaze_after_label",
          "1st_gaze_latency",
          "1st_gaze_duration",
          "2nd_gaze_after_label",
          "2nd_gaze_latency",
          "2nd_gaze_duration"
          ]

quant_columns = ["Baseline_LT-interesting",
                 "Baseline_LT-other",
                "Test_LT-interesting_BL-corr.",
                "Test_LT_other_BL-corr.",
                "Test_LT_interesting",
                "Test_LT_other",
                "Test_LT_familiars",
                "Look_before_end_of_label",
                "1st_gaze_after_label",
                "1st_gaze_latency",
                "1st_gaze_duration",
                "2nd_gaze_after_label",
                "2nd_gaze_latency",
                "2nd_gaze_duration"
                ]

aggr_columns = [
                "Test_LT_interesting",
                "Test_LT_other",
                "Test_LT_familiars",
                "Baseline_LT-interesting",
                "Baseline_LT-other",
                "Test_LT-interesting_BL-corr.",
                "Test_LT_other_BL-corr.",
                "First_gaze_on_interesting",
                "First_gaze_on_other",
                "Second_gaze_on_interesting",
                "Second_gaze_on_other"]


class Fam_data:

    def __init__(self, df):
        """
        df: dataframe containing the events
        """
        self.start_times = df[df["Event"]==FAM_DEMO]["TimeStamp"].tolist()
        self.end_times = [t+ fam_demo_dur for t in self.start_times]
        self.label_start_times = df[df["Event"]==FAM_LBL_START]["TimeStamp"].tolist()
        self.label_end_times = df[df["Event"]==FAM_LBL_END]["TimeStamp"].tolist()


class Teaching_data:

    def __init__(self, df):
        """
        df: dataframe containing the events
        s_times: list of logged start times; real start times are 3s later due to logging before "intro_with_face_start"
        """
        s_times = df[df["Event"].str.startswith("Familiarisation_anim", na=False)]["TimeStamp"].tolist()
        self.start_times = [x+3000 for x in s_times]
        self.end_times = [t+anim_dur for t in self.start_times]
        self.label_start_times = df[df["Event"]==TEACH_LBL_START]["TimeStamp"].tolist()
        self.label_end_times = df[df["Event"]==TEACH_LBL_END]["TimeStamp"].tolist()


class Test_data:

    def __init__(self, df):
        """
        df: dataframe containing the events
        """
        self.events = [str(e) for e in df[df["Event"].str.startswith(TEST_EVENT_STARTSWITH, na=False)]["Event"].tolist()]
        self.start_events = [e for e in self.events if e.endswith("STARTS")]
        self.end_events = [e for e in self.events if e.endswith("ENDS")]
        self.bl_start_times = df[df["Event"]==BASELINE_EVENT]["TimeStamp"].tolist()
        self.ag_start_times = df[df["Event"]==ATT_GETT_START]["TimeStamp"].tolist()
#        self.start_times = df[(df["Event"].str.startswith("test__", na=False)
#                            & df["Event"].str.endswith("STARTS", na=False))]["TimeStamp"].tolist()
        self.start_times = df[df["Event"].isin(self.start_events)]["TimeStamp"].tolist()
#        self.end_times = df[(df["Event"].str.startswith("test__", na=False)
#                            & df["Event"].str.endswith("ENDS", na=False))]["TimeStamp"].tolist()
        self.end_times = df[df["Event"].isin(self.end_events)]["TimeStamp"].tolist()


class Test_results:

    def __init__(self, subj_nr):
        self.subj_nr = subj_nr
        self.ag_looks = []
        self.all_test_onint_bl_corr = []
        self.all_test_onboring_bl_corr = []
        self.all_test_onint = []
        self.all_test_onboring = []
        self.all_test_onfam = []
        self.preceding_looks = []
        self.first_gazes = []
        self.first_gaze_latencies = []
        self.first_gaze_durations = []
        self.second_gazes = []
        self.second_gaze_latencies = []
        self.second_gaze_durations = []


