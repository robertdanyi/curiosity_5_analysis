#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""
#import constants_times_4 as c
#import logging
#import datetime
#import os


#logtime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
#log = os.path.join(c.DIR, "runlogs", "curiosity_calculations_{0}.log".format(logtime))
#logging.basicConfig(filename=log, level=logging.DEBUG)


def collect_gaze(df, freq=60, threshold=151):
    """
    input df: the slice of the original big dataframe,
    containing only the relevant rows
    """

    sample_time = 1000/freq # 16.7 ms
    min_sample_nr = int(threshold / sample_time) # 9 samples

    gaze_list = []

    hits = []
    for i in df.index:

        look = df.at[i, "aoi"]

        if look != "OUT":

            if not hits: # empty hits list
                hits.append(df.at[i, "TimeStamp"])
                hits.append(look)

            elif look in hits:
                hits.append(look)
                # if last row
                if (i == df.index[-1]) and (len(hits) >= min_sample_nr):
                    gaze_list.append(hits[:])

            else: # new aoi tag
                if len(hits) >= min_sample_nr:
                    gaze_list.append(hits[:])

                hits[:] = []
                hits.append(df.at[i, "TimeStamp"])
                hits.append(look)

        else:
            if len(hits) >= min_sample_nr:
                gaze_list.append(hits[:])
            hits[:] = []

    # tag_time_dur_dict: {rank:[tag, time, duration (lenght)]}
    tag_time_dur_dict = {}
    for i,gaze in enumerate(gaze_list):
        tag_time_dur_dict[i+1] = [gaze[-1], gaze[0], len(gaze[1:])]

    gaze = Gaze(tag_time_dur_dict)

    return gaze


class Gaze:
    """
    tag_time_dur_dict: {rank:[tag, time, duration (lenght)]}
    """

    def __init__(self, tag_time_dur_dict):
        self._dict = tag_time_dur_dict


    def get_taglist(self):

        taglist = []
        for v in self._dict.values():
            taglist.append(v[0])

        return taglist


    def get_gaze_data(self, gaze_nr):

        if gaze_nr in self._dict.keys():
            gaze_data = self._dict[gaze_nr]
            return gaze_data[0], gaze_data[1], gaze_data[2]
        else:
            return None, None, None


    def calculate_onobject_gaze(self):
        """
        Adds the lenghts of the gazes directed at the same object.
        'all_gaze' will be the sum of gazes directed at
        the interesting, the boring and the familiar objects.
        Returns cumulative gaze of each object kind proportional to 'all gaze'
        """
        onint_gaze, onboring_gaze, onfam_gaze = 0,0,0
        for k, v in self._dict.items():
            if v[0] == "INT":
                onint_gaze += v[2]
            elif v[0] == "BOR":
                onboring_gaze += v[2]
            elif v[0] == "FAM":
                onfam_gaze += v[2]

        all_gaze = onint_gaze + onboring_gaze + onfam_gaze
        onint = onint_gaze / all_gaze if all_gaze != 0 else 0
        onboring = onboring_gaze / all_gaze if all_gaze != 0 else 0
        onfam = onfam_gaze / all_gaze if all_gaze != 0 else 0

        return onint, onboring, onfam



def calculate_onscreen_gaze(dataframe, start_times, end_times):

    onscreen_looks = []

    for n in range(len(start_times)):
        df = dataframe[(dataframe["TimeStamp"] >= start_times[n]) & (dataframe["TimeStamp"]< end_times[n])]
        valid_times = df["gazepoints"].apply(lambda x : x != "invalid").sum()
        onscreen_looks.append(valid_times / df["gazepoints"].size)

    return onscreen_looks


