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
    
Change logs
From 2020-02-24: 
    - Corrected order in familiarisation: 
        "intro_with_face_start" comes BEFORE "Familiarisation_anim.."
    - New logline for test start:
        "test__intLabel:[bitye/tacok]:[bottom-right/..]_[banana/apple]:[top_right/..]_STARTS
    - Small change in logline for test end:
        "test__intLabel_ENDS / test__otherLabel_ENDS"
"""

import os

# sample time: 1000ms/60
freq = 60 # monitor refreshment rate (Hz / fps)
ST = 1000/freq # 16.66667 ms

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

second_int_side_dict = {"top-left":"bottom-right", "bottom-left":"top-right", "bottom-right":"top-left", "top-right":"bottom-left"}
int_side_pairs = [["top-left", "bottom-right"], ["bottom-left", "top-right"]]

# to get aois for the familiar objects as well.
DIAG1 = (AOI_top_left,AOI_bottom_right)
DIAG2 = (AOI_bottom_left,AOI_top_right)
AOI_screen = [DIAG1,DIAG2]

AOI_ag = [(960,600), 320,320] # x:760-1160, y:420-780

fam_demo_dur = 6000
anim_dur = 12533

# gaze structure
"""
Label onset is at 2100ms after ag_start.
Under 233ms latency after onset, and above 2000ms latency a gaze shift is not considered a response.
Swingley et al. 1999.: Mean 'no-overlap' response times for 24 month-olds is around 600 ms.
Since the "test start" is logged 572ms after label onset (at 2672), infants should start responding around the end of AG/label.

Define 2 test periods:
    - test gaze period: from ag_start+2333ms to ag_end+2000ms - to collect gazes 
        - initial gaze data as well
    - test look period: from ag_start+2333ms to test_end - to collect on object gazes
test_start = ag_start+2333 or test start time-339
"""
ER = -339 # early response from test_start
RSTART = 2333 # response start from ag_start
REND = 2000 # response end from test_start / ag_end


# event strings
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

    def __init__(self, df, oldlog):
        """
        df: dataframe containing the events
        oldlog: Boolean to check if older version of log (before 2020-02-24)
            start times are 3s later due to incorrect logging before "intro_with_face_start"
        ---------
        s_times: list of the logged familiarisation start times; 
        "teaching" = "familiarisation"
        """
        
        teaching_events_df = df[df["Event"].str.startswith("Familiarisation_anim", na=False)]
        s_times = teaching_events_df["TimeStamp"].tolist()
        
        self.start_times = self._get_start_times(s_times, oldlog)
        self.end_times = [t+anim_dur for t in self.start_times]
        self.label_start_times = df[df["Event"]==TEACH_LBL_START]["TimeStamp"].tolist()
        self.label_end_times = df[df["Event"]==TEACH_LBL_END]["TimeStamp"].tolist()
        self.interesting_sides = [e.split("_")[-1][:-1] for e in teaching_events_df["Event"].tolist()]
        
    
    def _get_start_times(self, s_times, oldlog):
        
        if oldlog:
            return s_times
        else:
            return [x+3000 for x in s_times]


class Test_controll_data:

    def __init__(self, df, oldlog):
        """
        df: dataframe containing the events
        """
        self.events = [str(e) for e in df[df["Event"].str.startswith(TEST_EVENT_STARTSWITH, na=False)]["Event"].tolist()]
        self.start_events = [e for e in self.events if e.endswith("STARTS")]
        self.end_events = [e for e in self.events if e.endswith("ENDS")]
        self.bl_start_times = df[df["Event"]==BASELINE_EVENT]["TimeStamp"].tolist()
        self.ag_start_times = df[df["Event"]==ATT_GETT_START]["TimeStamp"].tolist()
        self.start_times = df[df["Event"].isin(self.start_events)]["TimeStamp"].tolist()
        self.end_times = df[df["Event"].isin(self.end_events)]["TimeStamp"].tolist()
        self.interesting_sides = self._get_interesting_sides(oldlog)
        
        
    def _get_interesting_sides(self, oldlog):
        
        if oldlog: # in logfiles before 02-24
            # test__int_label_bottom_right_tacok_STARTS
            return ["-".join(e.split("_")[-4:-2]) for e in self.start_events]
        
        else:  
            # test__otherLabel:tacok:bottom-right_banana:top-right_STARTS
            first_int_side = self.start_events[0].split(":")[2].split("_")[0]
            second_int_side = second_int_side_dict[first_int_side]
            
            return [first_int_side, second_int_side]




